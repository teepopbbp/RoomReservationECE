from django.db import models
from django.utils import timezone


class RecurringGroup(models.Model):
    """Links bookings that were created together from a recurring pattern."""
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'กลุ่มการจองซ้ำ'


class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING,   'รอการอนุมัติ'),
        (STATUS_APPROVED,  'อนุมัติแล้ว'),
        (STATUS_REJECTED,  'ปฏิเสธ'),
        (STATUS_CANCELLED, 'ยกเลิก'),
    ]

    PURPOSE_TEACHING = 'teaching'
    PURPOSE_TRAINING = 'training'
    PURPOSE_CHOICES = [
        (PURPOSE_TEACHING, 'สอนปกติ/ชดเชย/เสริม'),
        (PURPOSE_TRAINING, 'จัดอบรม/จัดติว'),
    ]

    PROGRAM_BACHELOR = 'bachelor'
    PROGRAM_MASTER = 'master'
    PROGRAM_TEP = 'tep'
    PROGRAM_TUPINE = 'tupine'
    PROGRAM_CHOICES = [
        (PROGRAM_BACHELOR, 'ปริญญาตรีภาคปกติ'),
        (PROGRAM_MASTER,   'ปริญญาโท'),
        (PROGRAM_TEP,      'TEP-TEPE'),
        (PROGRAM_TUPINE,   'TU-PINE'),
    ]

    room = models.ForeignKey(
        'rooms.Room', on_delete=models.PROTECT, verbose_name='ห้อง'
    )
    booker = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.PROTECT,
        related_name='bookings', verbose_name='ผู้จอง'
    )
    recurring_group = models.ForeignKey(
        RecurringGroup, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bookings'
    )

    purpose_type = models.CharField(
        max_length=20, choices=PURPOSE_CHOICES, verbose_name='วัตถุประสงค์'
    )
    course_code = models.CharField(max_length=20, blank=True, verbose_name='รหัสวิชา')
    course_name = models.CharField(max_length=200, blank=True, verbose_name='ชื่อวิชา')
    program = models.CharField(
        max_length=20, choices=PROGRAM_CHOICES, blank=True, verbose_name='หลักสูตร'
    )
    event_name = models.CharField(max_length=200, blank=True, verbose_name='ชื่อเรื่อง')

    date = models.DateField(verbose_name='วันที่')
    start_time = models.TimeField(verbose_name='เวลาเริ่ม')
    end_time = models.TimeField(verbose_name='เวลาสิ้นสุด')

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_PENDING, verbose_name='สถานะ'
    )
    rejection_reason = models.TextField(blank=True, verbose_name='เหตุผลที่ปฏิเสธ')
    reviewed_by = models.ForeignKey(
        'accounts.CustomUser', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_bookings'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'การจอง'
        verbose_name_plural = 'การจอง'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.room} | {self.date} {self.start_time}–{self.end_time} | {self.booker}"

    @property
    def purpose_label(self):
        if self.purpose_type == self.PURPOSE_TEACHING:
            return f"{self.course_code} {self.course_name} ({self.get_program_display()})"
        return self.event_name

    @property
    def can_cancel(self):
        return (
            self.status in (self.STATUS_PENDING, self.STATUS_APPROVED)
            and self.date > timezone.localdate()
        )
