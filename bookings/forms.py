from django import forms
from django.core.exceptions import ValidationError

from rooms.models import Room
from .models import Booking

WEEKDAY_CHOICES = [
    (0, 'จันทร์'),
    (1, 'อังคาร'),
    (2, 'พุธ'),
    (3, 'พฤหัสบดี'),
    (4, 'ศุกร์'),
    (5, 'เสาร์'),
    (6, 'อาทิตย์'),
]

TIME_CHOICES = [(f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}')
                for h in range(7, 22) for m in (0, 30)]


class BookingForm(forms.Form):
    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(is_active=True),
        label='ห้อง',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    purpose_type = forms.ChoiceField(
        choices=Booking.PURPOSE_CHOICES,
        label='วัตถุประสงค์',
        widget=forms.RadioSelect,
    )
    # Teaching fields
    course_code = forms.CharField(
        max_length=20, required=False, label='รหัสวิชา',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    course_name = forms.CharField(
        max_length=200, required=False, label='ชื่อวิชา',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    program = forms.ChoiceField(
        choices=[('', '-- เลือกหลักสูตร --')] + Booking.PROGRAM_CHOICES,
        required=False, label='หลักสูตร',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    # Training field
    event_name = forms.CharField(
        max_length=200, required=False, label='ชื่อเรื่อง',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    # Schedule
    start_date = forms.DateField(
        label='วันเริ่มต้น',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    end_date = forms.DateField(
        label='วันสิ้นสุด',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        label='วันในสัปดาห์',
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    start_time = forms.ChoiceField(
        choices=TIME_CHOICES, label='เวลาเริ่ม',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    end_time = forms.ChoiceField(
        choices=TIME_CHOICES, label='เวลาสิ้นสุด',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def clean(self):
        data = super().clean()
        purpose = data.get('purpose_type')

        if purpose == Booking.PURPOSE_TEACHING:
            if not data.get('course_code'):
                self.add_error('course_code', 'กรุณาระบุรหัสวิชา')
            if not data.get('course_name'):
                self.add_error('course_name', 'กรุณาระบุชื่อวิชา')
            if not data.get('program'):
                self.add_error('program', 'กรุณาเลือกหลักสูตร')
        elif purpose == Booking.PURPOSE_TRAINING:
            if not data.get('event_name'):
                self.add_error('event_name', 'กรุณาระบุชื่อเรื่อง')

        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'วันสิ้นสุดต้องไม่ก่อนวันเริ่มต้น')

        start_time = data.get('start_time')
        end_time = data.get('end_time')
        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'เวลาสิ้นสุดต้องหลังเวลาเริ่ม')

        return data
