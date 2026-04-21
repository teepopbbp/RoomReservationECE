from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'full_name', 'email')
    ordering = ('username',)
    fieldsets = (
        (None, {'fields': ('username',)}),
        ('ข้อมูลส่วนตัว', {'fields': ('full_name', 'email')}),
        ('สิทธิ์', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'fields': ('username', 'role')}),
    )
