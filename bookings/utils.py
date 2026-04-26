from datetime import timedelta

from .models import Booking


def has_conflict(room, date, start_time, end_time, exclude_ids=()):
    """Return True if any pending/approved booking overlaps the given slot."""
    qs = Booking.objects.filter(
        room=room,
        date=date,
        status__in=(Booking.STATUS_PENDING, Booking.STATUS_APPROVED),
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude_ids:
        qs = qs.exclude(pk__in=exclude_ids)
    return qs.exists()


def generate_dates(start_date, end_date, weekdays):
    """
    Yield dates from start_date to end_date (inclusive) whose weekday()
    is in the weekdays set (0=Monday … 6=Sunday).
    """
    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays:
            yield current
        current += timedelta(days=1)
