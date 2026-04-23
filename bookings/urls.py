from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.my_bookings_view, name='list'),
    path('create/', views.create_booking_view, name='create'),
    path('<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel'),
    path('pending/', views.pending_bookings_view, name='pending'),
    path('<int:booking_id>/approve/', views.approve_booking_view, name='approve'),
    path('<int:booking_id>/reject/', views.reject_booking_view, name='reject'),
    path('calendar/', views.calendar_view, name='calendar'),
]
