from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('',                              views.dashboard_view,   name='dashboard'),
    # Rooms
    path('rooms/',                        views.room_list_view,   name='room_list'),
    path('rooms/add/',                    views.room_create_view, name='room_create'),
    path('rooms/<int:room_id>/edit/',     views.room_edit_view,   name='room_edit'),
    path('rooms/<int:room_id>/toggle/',   views.room_toggle_view, name='room_toggle'),
    path('rooms/<int:room_id>/delete/',   views.room_delete_view, name='room_delete'),
    # Users
    path('users/',                        views.user_list_view,   name='user_list'),
    path('users/<int:user_id>/toggle/',   views.user_toggle_view, name='user_toggle'),
    path('users/<int:user_id>/role/',     views.user_role_view,   name='user_role'),
    # Bookings
    path('bookings/',                     views.booking_list_view, name='booking_list'),
]
