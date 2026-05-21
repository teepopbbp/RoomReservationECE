from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, **extra_fields):
        extra_fields.setdefault('role', CustomUser.ROLE_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_LECTURER = 'lecturer'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_LECTURER, 'อาจารย์'),
        (ROLE_ADMIN, 'ผู้ดูแลระบบ'),
    ]

    username = models.CharField(max_length=150, unique=True, verbose_name='ชื่อผู้ใช้')
    email = models.EmailField(blank=True, verbose_name='อีเมล')
    full_name = models.CharField(max_length=255, blank=True, verbose_name='ชื่อ-นามสกุล')
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_LECTURER, verbose_name='บทบาท'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'ผู้ใช้'
        verbose_name_plural = 'ผู้ใช้'

    def __str__(self):
        return f"{self.full_name or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def display_name(self):
        return self.full_name or self.username
