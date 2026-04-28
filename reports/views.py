from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, ExpressionWrapper, DurationField
from django.shortcuts import redirect, render

from bookings.models import Booking
from rooms.models import Room


@login_required
def usage_report_view(request):
    if not request.user.is_admin:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')

    today = date.today()
    default_start = today.replace(day=1)
    default_end = today

    try:
        start_date = date.fromisoformat(request.GET.get('start', str(default_start)))
        end_date = date.fromisoformat(request.GET.get('end', str(default_end)))
    except ValueError:
        start_date = default_start
        end_date = default_end

    if end_date < start_date:
        end_date = start_date

    approved_qs = Booking.objects.filter(
        status=Booking.STATUS_APPROVED,
        date__range=[start_date, end_date],
    )

    rooms = Room.objects.filter(is_active=True)
    room_stats = []
    for room in rooms:
        room_bookings = approved_qs.filter(room=room)
        count = room_bookings.count()
        total_minutes = sum(
            (b.end_time.hour * 60 + b.end_time.minute) -
            (b.start_time.hour * 60 + b.start_time.minute)
            for b in room_bookings
        )
        days_in_range = (end_date - start_date).days + 1
        # Utilization: total booked hours vs available hours (8:00-20:00 = 12h/day)
        available_minutes = days_in_range * 12 * 60
        utilization = round(total_minutes / available_minutes * 100, 1) if available_minutes else 0

        teaching_count = room_bookings.filter(purpose_type=Booking.PURPOSE_TEACHING).count()
        training_count = room_bookings.filter(purpose_type=Booking.PURPOSE_TRAINING).count()

        room_stats.append({
            'room': room,
            'count': count,
            'hours': round(total_minutes / 60, 1),
            'utilization': utilization,
            'teaching_count': teaching_count,
            'training_count': training_count,
        })

    total_bookings = approved_qs.count()
    context = {
        'room_stats': room_stats,
        'start_date': start_date,
        'end_date': end_date,
        'total_bookings': total_bookings,
    }
    return render(request, 'reports/index.html', context)
