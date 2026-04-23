from django.contrib import admin

from .models import Booking, RecurringGroup


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('room', 'booker', 'date', 'start_time', 'end_time', 'purpose_type', 'status')
    list_filter = ('status', 'purpose_type', 'room')
    search_fields = ('booker__username', 'booker__full_name', 'course_name', 'event_name')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'reviewed_at', 'reviewed_by')


@admin.register(RecurringGroup)
class RecurringGroupAdmin(admin.ModelAdmin):
    list_display = ('pk', 'created_at')
