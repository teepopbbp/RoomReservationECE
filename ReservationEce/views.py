from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .services import authenticate_tu
from .models import User, Room
from django.contrib.auth.decorators import login_required


@login_required(login_url="login")
def home_view(request):
    rooms = Room.objects.filter(is_active=True)  # ดึงเฉพาะห้องที่เปิดใช้งาน
    return render(request, "ReservationEce/home.html", {"rooms": rooms})


def login_view(request):
    # ถ้า login อยู่แล้ว ไม่ต้องให้เข้าหน้า login อีก ส่งไปหน้า home เลย
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")

        tu_data = authenticate_tu(username_input, password_input)

        if tu_data and tu_data.get("status") == True:
            # ใช้ข้อมูลจาก API มาสร้างหรืออัปเดต User
            user, created = User.objects.update_or_create(
                username=tu_data.get("username"),
                defaults={
                    "first_name": tu_data.get("displayname_en", ""),
                    "email": tu_data.get("email", ""),
                    "tu_id": tu_data.get("username"),  # ปกติ username คือรหัสนักศึกษา
                    "role": "lecturer",
                },
            )
            login(request, user)
            return redirect("home")
        else:
            return render(
                request,
                "ReservationEce/login.html",
                {"error": "รหัสนักศึกษาหรือรหัสผ่านไม่ถูกต้อง"},
            )

    return render(request, "ReservationEce/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")
