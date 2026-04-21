from django.contrib import admin
from .models import User, Room, Booking


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "first_name", "last_name", "email", "role", "tu_id")


class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


admin.site.register(Booking)
