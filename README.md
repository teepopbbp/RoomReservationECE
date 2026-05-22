# ReservationENGR — CN334 HW1
## ข้อมูลกลุ่ม
| บทบาท | รหัสนักศึกษา | ชื่อ-สกุล |
|---------|-------------|----------------|
| หัวหน้า | 6610685361 | เสฏฐพัชร ญาณพัฒน์สร |
| สมาชิก | 6610685338 | ศุภกิตติ์ อัศววุฒิโรจน์ |
| สมาชิก | 6610685197 | ธีภพ บำบัดภัย |
## การแบ่งหน้าที่
| รหัสนักศึกษา | ความรับผิดชอบ |
|-------------|--------------------------------------|
| 6610685361 | Database & Base Setup (NFR-TECH), Authentication Module (FR-AUTH), Administration Module (FR-ADM) |
| 6610685338 | Booking Module (FR-BOOK), Approval Module (FR-APPR) |
| 6610685197 | Calendar Module (FR-CAL), Notification Module (FR-NOTI), Report Module (FR-RPT) |
## สิ่งที่ต้องติดตั้งก่อนรันโปรเจกต์
- ติดตั้ง Docker Desktop และเปิดใช้งานอยู่
- Port 8000 ต้องว่างอยู่
## วิธีรันโปรเจกต์
```bash
# 1. เริ่มต้น containers
docker compose up --build
# 2. เปิด terminal ใหม่ แล้วรัน migrations
docker compose exec web python manage.py migrate
# 3. โหลดข้อมูลตัวอย่าง
docker compose exec web python manage.py loaddata fixtures/initial_data.json
# 4. เปิดในเบราว์เซอร์
http://localhost:8000
```
## บัญชีสําหรับทดสอบ 
| บทบาท | Username | Password |
|-----------|----------|-----------|
| Admin | admin | admin1234 |
| ผู้ใช้งาน | testuser | test1234 |