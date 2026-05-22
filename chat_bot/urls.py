from django.urls import path
from . import views

app_name = "chat_bot"
urlpatterns = [
    # สั่งให้ลิ้งก์ /webhook/ วิ่งไปทำงานที่ฟังก์ชัน line_webhook ใน views
    path("", views.line_webhook, name="line_webhook"),
    # LINE Connect and Login Callback
    path("connect/", views.line_connect, name="line_connect"),
    path("login/callback/", views.line_login_callback, name="line_login_callback"),
]
