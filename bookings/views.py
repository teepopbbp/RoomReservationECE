import calendar as cal_module
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from notifications.utils import (
    send_booking_approved_email,
    send_booking_pending_email,
    send_booking_rejected_email,
    send_booking_cancelled_email,
)
from rooms.models import Room
from .forms import BookingForm
from .models import Booking, RecurringGroup
from .utils import generate_dates, has_conflict


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    upcoming = (
        Booking.objects
        .filter(booker=request.user, date__gte=today, status__in=(Booking.STATUS_PENDING, Booking.STATUS_APPROVED))
        .select_related('room')
        .order_by('date', 'start_time')[:5]
    )
    pending_count = Booking.objects.filter(status=Booking.STATUS_PENDING).count() if request.user.is_admin else None
    return render(request, 'dashboard.html', {
        'upcoming': upcoming,
        'pending_count': pending_count,
        'today': today,
    })


@login_required
def create_booking_view(request):
    form = BookingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        room = d['room']
        weekdays = {int(w) for w in d['weekdays']}
        start_time = time.fromisoformat(d['start_time'])
        end_time = time.fromisoformat(d['end_time'])

        dates = list(generate_dates(d['start_date'], d['end_date'], weekdays))
        if not dates:
            messages.error(request, 'ไม่พบวันที่ตรงกับเงื่อนไขที่เลือก')
            return render(request, 'bookings/create.html', {'form': form})

        conflicts = [dt for dt in dates if has_conflict(room, dt, start_time, end_time)]
        if conflicts:
            conflict_str = ', '.join(str(dt.strftime('%d/%m/%Y')) for dt in conflicts)
            messages.error(request, f'มีการจองซ้อนทับในวันต่อไปนี้: {conflict_str}')
            return render(request, 'bookings/create.html', {'form': form})

        group = RecurringGroup.objects.create() if len(dates) > 1 else None

        for dt in dates:
            Booking.objects.create(
                room=room,
                booker=request.user,
                recurring_group=group,
                purpose_type=d['purpose_type'],
                course_code=d.get('course_code', ''),
                course_name=d.get('course_name', ''),
                program=d.get('program', ''),
                event_name=d.get('event_name', ''),
                date=dt,
                start_time=start_time,
                end_time=end_time,
            )

        send_booking_pending_email(request.user, room, dates, start_time, end_time)
        messages.success(request, f'จองห้องเรียบร้อย {len(dates)} รายการ — รอการอนุมัติจาก Admin')
        return redirect('bookings:list')

    return render(request, 'bookings/create.html', {'form': form})


@login_required
def my_bookings_view(request):
    bookings = (
        Booking.objects
        .filter(booker=request.user)
        .select_related('room')
        .order_by('-date', '-start_time')
    )
    return render(request, 'bookings/list.html', {'bookings': bookings})


@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, booker=request.user)
    if not booking.can_cancel:
        messages.error(request, 'ไม่สามารถยกเลิกการจองนี้ได้')
        return redirect('bookings:list')
    if request.method == 'POST':
        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        send_booking_cancelled_email(booking)
        messages.success(request, 'ยกเลิกการจองเรียบร้อยแล้ว')
        return redirect('bookings:list')
    return render(request, 'bookings/cancel_confirm.html', {'booking': booking})


@login_required
def pending_bookings_view(request):
    if not request.user.is_admin:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')
    bookings = (
        Booking.objects
        .filter(status=Booking.STATUS_PENDING)
        .select_related('room', 'booker')
        .order_by('date', 'start_time')
    )
    return render(request, 'bookings/pending.html', {'bookings': bookings})


@login_required
def approve_booking_view(request, booking_id):
    if not request.user.is_admin:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')
    booking = get_object_or_404(Booking, pk=booking_id, status=Booking.STATUS_PENDING)
    if request.method == 'POST':
        booking.status = Booking.STATUS_APPROVED
        booking.reviewed_by = request.user
        booking.reviewed_at = timezone.now()
        booking.save()
        send_booking_approved_email(booking)
        messages.success(request, 'อนุมัติการจองเรียบร้อยแล้ว')
    return redirect('bookings:pending')


@login_required
def reject_booking_view(request, booking_id):
    if not request.user.is_admin:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')
    booking = get_object_or_404(Booking, pk=booking_id, status=Booking.STATUS_PENDING)
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, 'กรุณาระบุเหตุผลที่ปฏิเสธ')
            return redirect('bookings:pending')
        booking.status = Booking.STATUS_REJECTED
        booking.rejection_reason = reason
        booking.reviewed_by = request.user
        booking.reviewed_at = timezone.now()
        booking.save()
        send_booking_rejected_email(booking)
        messages.success(request, 'ปฏิเสธการจองเรียบร้อยแล้ว')
    return redirect('bookings:pending')


@login_required
def calendar_view(request):
    view_type = request.GET.get('view', 'week')
    room_id = request.GET.get('room', '')
    offset = int(request.GET.get('offset', 0))
    today = timezone.localdate()

    rooms = Room.objects.filter(is_active=True)
    selected_room = None
    if room_id:
        try:
            selected_room = rooms.get(pk=int(room_id))
        except (Room.DoesNotExist, ValueError):
            pass

    context = {
        'rooms': rooms,
        'selected_room': selected_room,
        'view_type': view_type,
        'offset': offset,
        'today': today,
    }

    if view_type == 'week':
        week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
        week_days = [week_start + timedelta(days=i) for i in range(7)]

        qs = Booking.objects.filter(
            date__range=[week_days[0], week_days[-1]],
            status__in=(Booking.STATUS_PENDING, Booking.STATUS_APPROVED),
        ).select_related('room', 'booker')
        if selected_room:
            qs = qs.filter(room=selected_room)

        day_bookings = {d: [] for d in week_days}
        for b in qs:
            if b.date in day_bookings:
                day_bookings[b.date].append(b)

        week_data = [(d, day_bookings[d]) for d in week_days]

        context.update({
            'week_data': week_data,
            'prev_offset': offset - 1,
            'next_offset': offset + 1,
        })

    else:  # month
        target_month = today.month + offset
        target_year = today.year + (target_month - 1) // 12
        target_month = ((target_month - 1) % 12) + 1
        first_day = date(target_year, target_month, 1)
        _, days_in_month = cal_module.monthrange(target_year, target_month)
        last_day = date(target_year, target_month, days_in_month)

        qs = Booking.objects.filter(
            date__range=[first_day, last_day],
            status__in=(Booking.STATUS_PENDING, Booking.STATUS_APPROVED),
        ).select_related('room', 'booker')
        if selected_room:
            qs = qs.filter(room=selected_room)

        # Build day number -> booking list
        date_bookings = {}
        for b in qs:
            date_bookings.setdefault(b.date.day, []).append(b)

        # Build calendar weeks [[day_number, ...], ...]  (0 = outside month)
        weeks = cal_module.monthcalendar(target_year, target_month)

        context.update({
            'month_year': first_day.strftime('%B %Y'),
            'month_label': f'{target_month:02d}/{target_year}',
            'weeks': weeks,
            'date_bookings': date_bookings,
            'prev_offset': offset - 1,
            'next_offset': offset + 1,
        })

    return render(request, 'bookings/calendar.html', context)
