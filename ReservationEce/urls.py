from django.urls import path
from . import views

urlpatterns = [
    # หน้าแรก (เช่น แสดงรายการห้อง)
    path("", views.home_view, name="home"),
    # ระบบ Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # ส่วนนี้ไว้ให้เพื่อนทำต่อ (เช่น รายละเอียดห้อง, การจอง)
    # path('room/<int:room_id>/', views.room_detail, name='room_detail'),
]
