import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger('notifications')


def _send(subject, body, recipients):
    recipients = [r for r in recipients if r]
    if not recipients:
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as e:
        logger.warning('Failed to send email "%s" to %s: %s', subject, recipients, e)


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

    subject_admin = f'[จองห้อง] คำขอจองห้อง {room.code} รอการอนุมัติ'
    body_admin = (
        f'มีคำขอจองห้องใหม่\n\n'
        f'ผู้จอง: {booker.display_name()} ({booker.username})\n'
        f'ห้อง: {room}\n'
        f'วันที่: {dates_str}\n'
        f'เวลา: {start_time.strftime("%H:%M")} – {end_time.strftime("%H:%M")}\n\n'
        f'กรุณาเข้าสู่ระบบเพื่ออนุมัติหรือปฏิเสธการจอง'
    )
    _send(subject_admin, body_admin, _admin_emails())

    if booker.email:
        subject_booker = f'[จองห้อง] ได้รับคำขอจองห้อง {room.code} แล้ว'
        body_booker = (
            f'เรียน {booker.display_name()}\n\n'
            f'ระบบได้รับคำขอจองห้องของคุณเรียบร้อยแล้ว กำลังรอการอนุมัติจากผู้ดูแลระบบ\n\n'
            f'ห้อง:  {room}\n'
            f'วันที่: {dates_str}\n'
            f'เวลา:  {start_time.strftime("%H:%M")} – {end_time.strftime("%H:%M")}\n'
            f'จำนวน: {len(dates)} วัน\n\n'
            f'คุณจะได้รับอีเมลแจ้งผลการอนุมัติอีกครั้ง\n\n'
            f'ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ มหาวิทยาลัยธรรมศาสตร์'
        )
        _send(subject_booker, body_booker, [booker.email])


def send_booking_approved_email(booking):
    if not booking.booker.email:
        return
    from bookings.models import Booking
    all_dates = (
        Booking.objects
        .filter(
            booker=booking.booker,
            room=booking.room,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose_type=booking.purpose_type,
            recurring_group=booking.recurring_group,
        )
        .order_by('date')
        .values_list('date', flat=True)
    )
    dates_str = ', '.join(d.strftime('%d/%m/%Y') for d in all_dates[:5])
    if len(all_dates) > 5:
        dates_str += f' ... (รวม {len(all_dates)} วัน)'

    subject = f'[จองห้อง] การจองห้อง {booking.room.code} ได้รับการอนุมัติ'
    body = (
        f'เรียน {booking.booker.display_name()}\n\n'
        f'การจองของคุณได้รับการอนุมัติแล้ว\n\n'
        f'ห้อง: {booking.room}\n'
        f'วันที่: {dates_str}\n'
        f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n'
        f'วัตถุประสงค์: {booking.purpose_label}\n\n'
        f'ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ มหาวิทยาลัยธรรมศาสตร์'
    )
    _send(subject, body, [booking.booker.email])


def send_booking_rejected_email(booking):
    if not booking.booker.email:
        return
    subject = f'[จองห้อง] การจองห้อง {booking.room.code} ถูกปฏิเสธ'
    body = (
        f'เรียน {booking.booker.display_name()}\n\n'
        f'การจองของคุณถูกปฏิเสธ\n\n'
        f'ห้อง: {booking.room}\n'
        f'วันที่: {booking.date.strftime("%d/%m/%Y")}\n'
        f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n'
        f'เหตุผล: {booking.rejection_reason}\n\n'
        f'ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ มหาวิทยาลัยธรรมศาสตร์'
    )
    _send(subject, body, [booking.booker.email])


def send_booking_cancelled_email(booking):
    subject = f'[จองห้อง] ยกเลิกการจองห้อง {booking.room.code}'
    body_admin = (
        f'การจองถูกยกเลิก\n\n'
        f'ผู้จอง: {booking.booker.display_name()}\n'
        f'ห้อง: {booking.room}\n'
        f'วันที่: {booking.date.strftime("%d/%m/%Y")}\n'
        f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n'
    )
    _send(subject, body_admin, _admin_emails())

    if booking.booker.email:
        body_booker = (
            f'เรียน {booking.booker.display_name()}\n\n'
            f'การจองของคุณถูกยกเลิกเรียบร้อยแล้ว\n\n'
            f'ห้อง: {booking.room}\n'
            f'วันที่: {booking.date.strftime("%d/%m/%Y")}\n'
            f'เวลา: {booking.start_time.strftime("%H:%M")} – {booking.end_time.strftime("%H:%M")}\n\n'
            f'ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ มหาวิทยาลัยธรรมศาสตร์'
        )
        _send(subject, body_booker, [booking.booker.email])
