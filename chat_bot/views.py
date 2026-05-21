import json
import os
from datetime import datetime, date, timedelta
from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

# ไลบรารี LINE Bot SDK (เวอร์ชัน 3)
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# ไลบรารี Gemini API
import google.generativeai as genai


from bookings.models import Booking
from rooms.models import Room
from accounts.models import CustomUser
from accounts.models import CustomUser

configuration = Configuration(access_token=os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")


@csrf_exempt
def line_webhook(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # ตรวจสอบ Signature จาก LINE เพื่อความปลอดภัย
    signature = request.META.get("HTTP_X_LINE_SIGNATURE", "")
    body = request.body.decode("utf-8")

    try:
        # ส่งข้อมูลไปให้ฟังก์ชันจัดการประมวลผลต่อ
        handler.handle(body, signature)
    except InvalidSignatureError:
        return HttpResponse(status=400)

    return HttpResponse(status=200)


# ฟังก์ชันหลักเมื่อมีข้อความตัวอักษรพิมพ์เข้ามาใน LINE
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    current_date = date.today().isoformat()

    # 1. เขียน Prompt เหมือนเวอร์ชัน Node.js เป๊ะๆ
    prompt = f"""
    คุณคือ AI ผู้ช่วยจองห้องของคณะวิศวกรรมศาสตร์ มหาวิทยาลัยธรรมศาสตร์ ดึงข้อมูลจากข้อความ: "{user_message}"
    วันเวลาปัจจุบันคือ: {current_date}
    ให้ออกมาเป็น JSON format ตามโครงสร้างนี้เท่านั้น:
    {{
      "intent": "booking", 
      "room_name": "ชื่อห้องที่ต้องการจอง (เช่น ห้องประชุม 1, ห้องบรรยาย 1) ถ้าไม่ระบุให้เป็น null",
      "date": "วันที่จอง (รูปแบบ YYYY-MM-DD) ถ้าไม่ระบุเป็น null",
      "start_time": "เวลาเริ่ม (รูปแบบ HH:MM:00) ถ้าไม่ระบุเป็น null",
      "end_time": "เวลาสิ้นสุด (รูปแบบ HH:MM:00) ถ้าผู้ใช้ไม่ระบุ ให้บวกเพิ่ม 1 ชั่วโมงจาก start_time"
    }}
    """

    try:
        # เรียกใช้งาน Gemini บังคับตอบเป็น JSON
        response = gemini_model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )
        booking_data = json.loads(response.text)

        reply_text = ""

        if booking_data.get("intent") != "booking":
            reply_text = "ขอโทษครับ ผมรับหน้าที่จัดการเรื่องจองห้องเท่านั้น ต้องการจองห้องไหน วันและเวลาใดครับ?"
        elif (
            not booking_data.get("room_name")
            or not booking_data.get("date")
            or not booking_data.get("start_time")
        ):
            reply_text = f"ข้อมูลไม่ครบครับ ขาด: {'[ชื่อห้อง] ' if not booking_data.get('room_name') else ''}{'[วันที่] ' if not booking_data.get('date') else ''}{'[เวลา]' if not booking_data.get('start_time') else ''} รบกวนพิมพ์บอกอีกครั้งครับ"
        else:
            room_name = booking_data["room_name"]
            booking_date = booking_data["date"]
            start_time = booking_data["start_time"]
            end_time = booking_data["end_time"]

            # 2. ค้นหาห้องด้วย Django ORM
            try:
                room = Room.objects.get(name=room_name)

                # 3. ตรวจสอบคิวที่ซ้อนทับกันด้วย Django ORM
                is_overlapped = Booking.objects.filter(
                    room=room,
                    date=booking_date,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                ).exists()

                if is_overlapped:
                    reply_text = f"❌ ขออภัยครับ ห้อง {room_name} มีผู้จองแล้วในช่วงเวลา {start_time[:-3]} - {end_time[:-3]} ลองเปลี่ยนเวลาดูไหมครับ?"
                else:
                    # 4. สวมรอยดึงผู้ใช้คนแรกในตารางมาจอง (เวอร์ชัน Test)
                    booker = CustomUser.objects.first()

                    if not booker:
                        reply_text = (
                            "❌ ไม่สามารถจองได้ เนื่องจากระบบยังไม่มีบัญชีผู้ใช้ใดๆ"
                        )
                    else:
                        # 5. บันทึกข้อมูลลงฐานข้อมูลผ่าน Django ORM ตัวเดียวจบ!
                        # ระบบจะคอยกรอก created_at, updated_at และคอลัมน์อื่นๆ ที่เป็น default ให้เอง
                        Booking.objects.create(
                            date=booking_date,
                            start_time=start_time,
                            end_time=end_time,
                            event_name="จองผ่าน LINE Chatbot",
                            status="Confirmed",
                            room=room,
                            purpose_type="other",
                            course_code="-",
                            course_name="-",
                            program="-",
                            rejection_reason="-",
                            booker=booker,
                        )
                        reply_text = f"✅ จองห้องสำเร็จเรียบร้อยแล้ว!\n\nสรุปการจอง:\n- ห้อง: {room_name}\n- วันที่: {booking_date}\n- เวลา: {start_time[:-3]} ถึง {end_time[:-3]}\n\nขอบคุณที่ใช้บริการครับ"

            except Room.DoesNotExist:
                reply_text = f'❌ ไม่พบห้องที่ชื่อ "{room_name}" ในระบบครับ กรุณาตรวจสอบชื่อห้องอีกครั้ง'

    except Exception as e:
        print(f"System Error: {e}")
        reply_text = "ระบบ AI หรือฐานข้อมูลขัดข้อง กรุณาลองใหม่อีกครั้งครับ"

    # ส่งข้อความกลับไปหาผู้ใช้ทาง LINE
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]
            )
        )
