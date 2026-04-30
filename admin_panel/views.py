import functools
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import CustomUser
from bookings.models import Booking
from rooms.models import Room
from .forms import RoomForm


def admin_required(view_func):
    @functools.wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return login_required(wrapped)


# ── Dashboard ──────────────────────────────────────────────────────────────

@admin_required
def dashboard_view(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    context = {
        'active_rooms':    Room.objects.filter(is_active=True).count(),
        'total_rooms':     Room.objects.count(),
        'total_users':     CustomUser.objects.count(),
        'admin_users':     CustomUser.objects.filter(role=CustomUser.ROLE_ADMIN).count(),
        'pending_count':   Booking.objects.filter(status=Booking.STATUS_PENDING).count(),
        'approved_month':  Booking.objects.filter(status=Booking.STATUS_APPROVED, date__gte=month_start).count(),
        'rejected_count':  Booking.objects.filter(status=Booking.STATUS_REJECTED).count(),
        'cancelled_count': Booking.objects.filter(status=Booking.STATUS_CANCELLED).count(),
        'recent_bookings': (
            Booking.objects
            .select_related('room', 'booker')
            .order_by('-created_at')[:8]
        ),
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ── Rooms ──────────────────────────────────────────────────────────────────

@admin_required
def room_list_view(request):
    rooms = Room.objects.order_by('code')
    return render(request, 'admin_panel/rooms/list.html', {'rooms': rooms})


@admin_required
def room_create_view(request):
    form = RoomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'เพิ่มห้องเรียบร้อยแล้ว')
        return redirect('admin_panel:room_list')
    return render(request, 'admin_panel/rooms/form.html', {'form': form, 'title': 'เพิ่มห้องใหม่'})


@admin_required
def room_edit_view(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    form = RoomForm(request.POST or None, instance=room)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'แก้ไขข้อมูลห้องเรียบร้อยแล้ว')
        return redirect('admin_panel:room_list')
    return render(request, 'admin_panel/rooms/form.html', {'form': form, 'title': 'แก้ไขห้อง', 'room': room})


@admin_required
def room_toggle_view(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(Room, pk=room_id)
        room.is_active = not room.is_active
        room.save()
        label = 'เปิดใช้งาน' if room.is_active else 'ปิดใช้งาน'
        messages.success(request, f'{label}ห้อง {room.code} เรียบร้อยแล้ว')
    return redirect('admin_panel:room_list')


@admin_required
def room_delete_view(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(Room, pk=room_id)
        active_bookings = Booking.objects.filter(
            room=room, status__in=(Booking.STATUS_PENDING, Booking.STATUS_APPROVED)
        )
        if active_bookings.exists():
            messages.error(request, f'ไม่สามารถลบห้อง {room.code} ได้ มีการจองที่ยังใช้งานอยู่')
        else:
            name = room.code
            room.delete()
            messages.success(request, f'ลบห้อง {name} เรียบร้อยแล้ว')
    return redirect('admin_panel:room_list')


# ── Users ──────────────────────────────────────────────────────────────────

@admin_required
def user_list_view(request):
    users = CustomUser.objects.order_by('role', 'full_name')
    return render(request, 'admin_panel/users/list.html', {'users': users})


@admin_required
def user_toggle_view(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, pk=user_id)
        if user == request.user:
            messages.error(request, 'ไม่สามารถปิดใช้งานบัญชีของตัวเองได้')
        else:
            user.is_active = not user.is_active
            user.save()
            label = 'เปิดใช้งาน' if user.is_active else 'ระงับ'
            messages.success(request, f'{label}บัญชี {user.display_name()} เรียบร้อยแล้ว')
    return redirect('admin_panel:user_list')


@admin_required
def user_role_view(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, pk=user_id)
        new_role = request.POST.get('role')
        if new_role in (CustomUser.ROLE_LECTURER, CustomUser.ROLE_ADMIN):
            user.role = new_role
            user.save()
            messages.success(request, f'เปลี่ยนบทบาทของ {user.display_name()} เรียบร้อยแล้ว')
        else:
            messages.error(request, 'บทบาทไม่ถูกต้อง')
    return redirect('admin_panel:user_list')


# ── Bookings ───────────────────────────────────────────────────────────────

@admin_required
def booking_list_view(request):
    status_filter = request.GET.get('status', '')
    room_filter   = request.GET.get('room', '')

    qs = Booking.objects.select_related('room', 'booker', 'reviewed_by').order_by('-date', '-start_time')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if room_filter:
        qs = qs.filter(room_id=room_filter)

    context = {
        'bookings':       qs[:150],
        'rooms':          Room.objects.filter(is_active=True),
        'status_filter':  status_filter,
        'room_filter':    room_filter,
        'status_choices': Booking.STATUS_CHOICES,
    }
    return render(request, 'admin_panel/bookings/list.html', context)
