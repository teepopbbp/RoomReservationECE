from django.urls import path
from . import views

urlpatterns = [
    # สั่งให้ลิ้งก์ /webhook/ วิ่งไปทำงานที่ฟังก์ชัน line_webhook ใน views
    path("", views.line_webhook, name="line_webhook"),
]
