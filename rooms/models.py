from django.db import models


class Room(models.Model):
    TYPE_MEETING = 'meeting'
    TYPE_CLASSROOM = 'classroom'
    TYPE_CHOICES = [
        (TYPE_MEETING, 'ห้องประชุม'),
        (TYPE_CLASSROOM, 'ห้องเรียน'),
    ]

    code = models.CharField(max_length=20, unique=True, verbose_name='รหัสห้อง')
    name = models.CharField(max_length=100, verbose_name='ชื่อห้อง')
    room_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, verbose_name='ประเภท'
    )
    capacity = models.PositiveIntegerField(verbose_name='จำนวนที่นั่ง')
    is_active = models.BooleanField(default=True, verbose_name='เปิดใช้งาน')

    class Meta:
        verbose_name = 'ห้อง'
        verbose_name_plural = 'ห้อง'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} – {self.name}"
