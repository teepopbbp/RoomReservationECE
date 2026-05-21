import json
import os
import traceback
from datetime import datetime, date, timedelta
from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.cache import cache

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

configuration = Configuration(access_token=os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-3.1-flash-lite")


@csrf_exempt
def line_webhook(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    signature = request.META.get("HTTP_X_LINE_SIGNATURE", "")
    body = request.body.decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return HttpResponse(status=400)

    return HttpResponse(status=200)


# ฟังก์ชันหลักเมื่อมีข้อความตัวอักษรพิมพ์เข้ามาใน LINE
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    current_date = date.today().isoformat()

    # 1. ดึงประวัติการคุยเก่า และ "สมุดจด (State)" จาก Cache
    cache_key = f"chat_history_{user_id}"
    state_key = f"chat_state_{user_id}"  # สร้างกระเป๋าความจำใหม่สำหรับ JSON

    chat_history = cache.get(cache_key, "")
    current_state = cache.get(state_key, {})  # ดึงข้อมูลที่ AI เคยสกัดไว้รอบที่แล้ว

    # 2. เอาข้อความใหม่ไปต่อท้ายประวัติเดิม
    chat_history += f"\nลูกค้า: {user_message}"

    # 3. เขียน Prompt โดยส่ง "สมุดจด" ไปให้ AI ดูด้วย
    prompt = f"""
    คุณคือพนักงานรับจองห้องประชุมของมหาวิทยาลัย ที่รับการจองห้องโดยมีอาจารย์และบุคลากรของมหาวิทยาลัยเป็นผู้ใช้งาน
    ข้อมูลอ้างอิง: วันนี้คือ {current_date}
    
    === ข้อมูลที่คุณรวบรวมได้แล้วในรอบที่แล้ว (Memory State) ===
    {json.dumps(current_state, ensure_ascii=False, indent=2)}
    =======================================================
    
    --- ประวัติการสนทนาทั้งหมด ---{chat_history}
    ----------------------

    คำสั่ง: ตรวจสอบประวัติการสนทนาและ "ข้อมูลที่คุณรวบรวมได้แล้ว" แล้วตอบกลับเป็น JSON เท่านั้น
    
    กฎเหล็ก:
    1. ห้ามลืมของเก่าเด็ดขาด: ให้นำข้อมูลจากกล่อง "Memory State" มารวมกับข้อความใหม่ของลูกค้า แล้วใส่ลงใน extracted_data ห้ามให้ข้อมูลที่เคยมีแล้วหายไป!
    2. ถามรวบยอดในครั้งเดียว: หากยังมีข้อมูล "ขาดหายไป" ให้ลิสต์สิ่งที่ขาดทั้งหมด และถามกลับในข้อความเดียว ห้ามถามทีละคำถาม
    3. ข้อมูลที่จำเป็นต้องมี:
       - พื้นฐาน: ชื่อห้อง (room), วันที่ (date YYYY-MM-DD), เวลาเริ่ม (start_time HH:MM), เวลาสิ้นสุด (end_time HH:MM), ประเภท (purpose_type วิเคราะห์เป็น teaching หรือ training)
       - ถ้า teaching: รหัสวิชา (course_code), ชื่อวิชา (course_name), หลักสูตร (program)
       - ถ้า training: ชื่องาน (event_name)
       *(หมายเหตุ: รหัสวิชาขึ้นต้นด้วยอักษร 2 ตัวตามด้วยเลข 3 ตัว เช่น CN334, หลักสูตรมีแค่ ปริญญาตรีภาคปกติ, ปริญญาโท, TEP-TEPE, TU-PINE)*
        
    โครงสร้าง JSON ที่ต้องส่งกลับ:
    {{
        "extracted_data": {{
            "room": "...",
            "date": "...",
            "start_time": "...",
            "end_time": "...",
            "purpose_type": "...",
            "course_code": "...",
            "course_name": "...",
            "program": "...",
            "event_name": "..."
        }},
        "status": "(ใส่ 'complete' ถ้าครบ หรือ 'incomplete' ถ้าขาด)",
        "reply_message": "(หาก incomplete ให้ถามสิ่งที่ขาดทั้งหมดอย่างสุภาพ ห้ามถามสิ่งที่อยู่ใน extracted_data แล้ว)"
    }}
    """

    try:
        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()

        reply_text = ""
        is_complete = False
        booking_data = {}  # เตรียมตัวแปรไว้เก็บสมุดจด

        try:
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            booking_data = data.get("extracted_data", {})
            status = data.get("status", "incomplete")
            reply_text = data.get(
                "reply_message", "ขออภัยครับ รบกวนแจ้งข้อมูลอีกครั้งครับ"
            )

            if status == "complete":
                is_complete = True
                room_name = booking_data.get("room")
                booking_date = booking_data.get("date")
                start_time = booking_data.get("start_time")
                end_time = booking_data.get("end_time")
                purpose_type = booking_data.get("purpose_type")

                try:
                    room = Room.objects.get(name__icontains=room_name)

                    is_overlapped = Booking.objects.filter(
                        room=room,
                        date=booking_date,
                        start_time__lt=end_time,
                        end_time__gt=start_time,
                    ).exists()

                    if is_overlapped:
                        reply_text = f"❌ ขออภัยครับ ห้อง {room.name} มีผู้จองแล้วในช่วงเวลา {start_time} - {end_time} ลองเปลี่ยนเวลาดูไหมครับ?"
                        is_complete = False
                    else:
                        booker = CustomUser.objects.first()
                        if not booker:
                            reply_text = (
                                "❌ ไม่สามารถจองได้ เนื่องจากระบบยังไม่มีบัญชีผู้ใช้ใดๆ"
                            )
                        else:
                            Booking.objects.create(
                                date=booking_date,
                                start_time=start_time,
                                end_time=end_time,
                                room=room,
                                booker=booker,
                                purpose_type=purpose_type,
                                course_code=booking_data.get("course_code") or "",
                                course_name=booking_data.get("course_name") or "",
                                program=booking_data.get("program") or "",
                                event_name=booking_data.get("event_name") or "",
                                status=Booking.STATUS_PENDING,
                            )
                            reply_text = f"✅ จองห้องสำเร็จเรียบร้อยแล้ว!\n\nสรุปการจอง:\n- ห้อง: {room.name}\n- วันที่: {booking_date}\n- เวลา: {start_time} ถึง {end_time}\n- สถานะ: รอการอนุมัติ\n\nขอบคุณที่ใช้บริการครับ"

                except Room.DoesNotExist:
                    reply_text = f'❌ ไม่พบห้องที่ชื่อ "{room_name}" ในระบบครับ กรุณาตรวจสอบชื่อห้องอีกครั้ง'
                    is_complete = False
                except Room.MultipleObjectsReturned:
                    reply_text = f'❌ พบห้องที่ชื่อคล้ายกับ "{room_name}" หลายห้อง รบกวนระบุให้ชัดเจนครับ'
                    is_complete = False

        except json.JSONDecodeError:
            reply_text = "ขออภัยครับ AI สับสนรูปแบบข้อมูล รบกวนพิมพ์บอกอีกครั้งครับ"

        # 4. อัปเดตประวัติการสนทนา และ "สมุดจด (State)" ลง Cache
        if is_complete:
            # จบงาน ลบความจำทิ้งทั้งคู่
            cache.delete(cache_key)
            cache.delete(state_key)
        else:
            chat_history += f"\nAI: {reply_text}"
            cache.set(cache_key, chat_history, timeout=300)
            # สำคัญที่สุด! เซฟ JSON ข้อมูลที่หาได้ล่าสุดเอาไว้ให้ AI อ่านรอบหน้า
            cache.set(state_key, booking_data, timeout=300)

    except Exception as e:
        print(f"System Error: {e}", flush=True)
        import traceback

        traceback.print_exc()
        reply_text = f"🚨 ระบบขัดข้อง 🚨\nตัวการคือ: {str(e)}"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]
            )
        )
