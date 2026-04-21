from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("lecturer", "Lecturer"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="lecturer")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    tu_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)


class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default="pending")

    class Meta:
        ordering = ["-start_time"]
