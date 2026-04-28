from django.conf import settings
from django.core.mail import send_mail


def _send(subject, body, recipients):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[r for r in recipients if r],
            fail_silently=True,
        )
    except Exception:
        pass


def _admin_emails():
    from accounts.models import CustomUser
    emails = list(
        CustomUser.objects.filter(role=CustomUser.ROLE_ADMIN, is_active=True)
        .values_list('email', flat=True)
    )
    if settings.ADMIN_EMAIL:
        emails.append(settings.ADMIN_EMAIL)
    return list(set(e for e in emails if e))


def send_booking_pending_email(booker, room, dates, start_time, end_time):
    dates_str = ', '.join(d.strftime('%d/%m/%Y') for d in dates[:5])
    if len(dates) > 5:
        dates_str += f' ... (รวม {len(dates)} วัน)'
    subject = f'[จองห้อง] คำขอจองห้อง {room.code} รอการอนุมัติ'
    body = (
        f'มีคำขอจองห้องใหม่\n\n'
        f'ผู้จอง: {booker.display_name()} ({booker.username})\n'
        f'ห้อง: {room}\n'
        f'วันที่: {dates_str}\n'
        f'เวลา: {start_time.strftime("%H:%M")} – {end_time.strftime("%H:%M")}\n\n'
        f'กรุณาเข้าสู่ระบบเพื่ออนุมัติหรือปฏิเสธการจอง'
    )
    _send(subject, body, _admin_emails())


def send_booking_approved_email(booking):
    if not booking.booker.email:
        return
    subject = f'[จองห้อง] การจองห้อง {booking.room.code} ได้รับการอนุมัติ'
    body = (
        f'การจองของคุณได้รับการอนุมัติแล้ว\n\n'
        f'ห้อง: {booking.room}\n'
        f'วันที่: {booking.date.strftime("%d/%m/%Y")}\n'
        f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n'
        f'วัตถุประสงค์: {booking.purpose_label}\n'
    )
    _send(subject, body, [booking.booker.email])


def send_booking_rejected_email(booking):
    if not booking.booker.email:
        return
    subject = f'[จองห้อง] การจองห้อง {booking.room.code} ถูกปฏิเสธ'
    body = (
        f'การจองของคุณถูกปฏิเสธ\n\n'
        f'ห้อง: {booking.room}\n'
        f'วันที่: {booking.date.strftime("%d/%m/%Y")}\n'
        f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n'
        f'เหตุผล: {booking.rejection_reason}\n'
    )
    _send(subject, body, [booking.booker.email])


def send_booking_cancelled_email(booking):
    subject = f'[จองห้อง] ยกเลิกการจองห้อง {booking.room.code}'
    body = (
        f'การจองถูกยกเลิก\n\n'
        f'ผู้จอง: {booking.booker.display_name()}\n'
        f'ห้อง: {booking.room}\n'
        f'วันที่: {booking.date.strftime("%d/%m/%Y")}\n'
        f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n'
    )
    _send(subject, body, _admin_emails())
