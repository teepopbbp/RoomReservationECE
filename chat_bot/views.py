import json
import os
import traceback
from datetime import datetime, date, timedelta
from django.http import (
    HttpResponse,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    JsonResponse,
)
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages

# ไลบรารี LINE Bot SDK (เวอร์ชัน 3)
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    URIAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    MemberJoinedEvent,
    MemberLeftEvent,
)

# ไลบรารี Gemini API
import google.generativeai as genai

from bookings.models import Booking
from rooms.models import Room
from accounts.models import CustomUser
from django.conf import settings
from urllib.parse import urlencode

# LINE Configuration
configuration = Configuration(access_token=os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-3.1-flash-lite")

# LINE Login Configuration
LINE_LOGIN_CHANNEL_ID = os.environ.get("LINE_LOGIN_CHANNEL_ID")
LINE_LOGIN_CHANNEL_SECRET = os.environ.get("LINE_LOGIN_CHANNEL_SECRET")
LINE_LOGIN_REDIRECT_URI = os.environ.get(
    "LINE_LOGIN_REDIRECT_URI", "http://localhost:8000/webhook/login/callback/"
)


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


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    current_date = date.today().isoformat()

    # 1. ดึงประวัติการคุยเก่า และ สร้างโครงสร้าง "สมุดจด" เริ่มต้น
    cache_key = f"chat_history_{user_id}"
    state_key = f"chat_state_{user_id}"

    chat_history = cache.get(cache_key, "")

    # กำหนดโครงสร้างข้อมูลให้ครบ เพื่อกัน Python เอ๋อ
    default_state = {
        "room": "",
        "date": "",
        "start_time": "",
        "end_time": "",
        "purpose_type": "",
        "course_code": "",
        "course_name": "",
        "program": "",
        "event_name": "",
    }
    current_state = cache.get(state_key, default_state)

    # 2. ต่อประวัติข้อความ
    chat_history += f"\nลูกค้า: {user_message}"

    # 3. Prompt: เอาสมุดจด (State) วางไว้บนสุดให้ AI เห็นชัดๆ ว่ามีอะไรแล้วบ้าง
    prompt = f"""
    คุณคือพนักงานรับจองห้องประชุมของมหาวิทยาลัย ที่รับการจองห้องโดยมีอาจารย์และบุคลากรของมหาวิทยาลัยเป็นผู้ใช้งาน
    ข้อมูลอ้างอิง: วันนี้คือ {current_date}
    
    [ข้อมูลที่รวบรวมได้แล้วในระบบ]
    {json.dumps(current_state, ensure_ascii=False, indent=2)}
    
    [ประวัติการสนทนาทั้งหมด]
    {chat_history}

    คำสั่ง: นำ "ข้อมูลที่รวบรวมได้แล้ว" มาผนวกกับข้อมูลใหม่ใน "ประวัติการสนทนา" และตอบกลับเป็น JSON
    
    กฎเหล็กที่ต้องปฏิบัติตามอย่างเคร่งครัด:
    1. ห้ามดัดแปลงหรือย่อข้อมูลเก่าเด็ดขาด: ข้อมูลใดที่มีค่าอยู่แล้วใน [ข้อมูลที่รวบรวมได้แล้วในระบบ] ให้คุณ "คัดลอก" ค่านั้นมาใส่ใน extracted_data ให้เหมือนเดิมเป๊ะๆ ทุกตัวอักษร (เช่น ถ้าของเดิมคือ "ห้องประชุม 2" ห้ามแก้เป็น "2" เด็ดขาด) ยกเว้นลูกค้าสั่งเปลี่ยนข้อมูล
    2. ห้ามถามซ้ำ: ข้อมูลไหนที่ลูกค้าบอกมาแล้ว และถูกบันทึกใน extracted_data แล้ว ห้ามทวงถามซ้ำเด็ดขาด!
    3. ถามรวบยอดในครั้งเดียว: หากตรวจสอบแล้วพบว่ายังมีข้อมูลจำเป็นที่ "ขาดหายไป" ให้คุณลิสต์สิ่งที่ขาดทั้งหมด และถามลูกค้ากลับในข้อความเดียว ห้ามถามทีละคำถาม (เพื่อประหยัดเวลา)
    4. ข้อมูลที่จำเป็นต้องมีให้ครบใน extracted_data :
       - ข้อมูลพื้นฐาน (ต้องมีเสมอ): ชื่อห้อง (room), วันที่ (date YYYY-MM-DD), เวลาเริ่ม (start_time HH:MM), เวลาสิ้นสุด (end_time HH:MM), ประเภท (purpose_type วิเคราะห์เป็น teaching หรือ training)
       - ถ้า purpose_type = teaching ต้องมีเพิ่ม: รหัสวิชา (course_code), ชื่อวิชา (course_name), หลักสูตร (program)
       - ถ้า purpose_type = training ต้องมีเพิ่ม: ชื่องาน/กิจกรรม (event_name)
       
    เงื่อนไขรูปแบบของข้อมูล:
       - รหัสวิชา: จะต้องขึ้นด้วยตัวอักษรภาษาอังกฤษสองตัวและตามด้วยตัวเลขสามตัว เช่น CN201, CN331, CN202, CN334
       - หลักสูตร: ตอนนี้มีหลักสูตรแค่ ปริญญาตรีภาคปกติ, ปริญญาโท, TEP-TEPE, TU-PINE
       
    โครงสร้าง JSON ที่ต้องส่งกลับ (ห้ามมีข้อความธรรมดานอกกรอบ JSON):
    {{
        "extracted_data": {{
            "room": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "date": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "start_time": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "end_time": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "purpose_type": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "course_code": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "course_name": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "program": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")",
            "event_name": "(ข้อมูลที่หาเจอ ถ้าไม่มีให้ใส่ "")"
        }},
        "status": "(ใส่ 'complete' เมื่อข้อมูลจำเป็นครบ หรือ 'incomplete' หากยังขาด)",
        "reply_message": "(หาก incomplete ให้พิมพ์ถามสิ่งที่ขาดหายไป 'ทั้งหมดในครั้งเดียว' อย่างสุภาพ เช่น 'รบกวนขอทราบ ชื่อห้อง, วันที่, และเวลาเริ่ม-สิ้นสุด ด้วยครับ' ห้ามถามทีละอย่าง. หาก complete ให้ใส่ "")"
    }}
    """

    try:
        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()

        reply_text = ""
        is_complete = False
        booking_data = {}

        try:
            # ใช้ Regex ช่วยจับ JSON เผื่อ AI พิมพ์ข้อความแปลกๆ ปนมา
            import re

            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                clean_json = match.group(0)

            data = json.loads(clean_json)

            ai_extracted = data.get("extracted_data", {})
            status = data.get("status", "incomplete")
            reply_text = data.get(
                "reply_message", "ขออภัยครับ รบกวนแจ้งข้อมูลอีกครั้งครับ"
            )

            # --- 🔥 MAGIC FIX: Python State Merge 🔥 ---
            # บังคับเอาข้อมูลเก่าจากระบบ มาเติมเต็มส่วนที่ AI อาจจะลืม!
            booking_data = default_state.copy()
            for key, old_value in current_state.items():
                new_value = ai_extracted.get(key, "")
                # ถ้า AI หาข้อมูลใหม่เจอ ให้ใช้อันใหม่, แต่ถ้า AI ส่งค่าว่างมา ให้ใช้ของเก่า!
                if (
                    new_value
                    and str(new_value).strip() != ""
                    and str(new_value).lower() != "null"
                ):
                    booking_data[key] = str(new_value).strip()
                else:
                    booking_data[key] = old_value
            # ----------------------------------------

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
                        # Look up user by LINE User ID
                        try:
                            booker = CustomUser.objects.get(line_user_id=user_id)
                        except CustomUser.DoesNotExist:
                            # User hasn't connected their LINE account yet
                            reply_text = (
                                f"❌ ยังไม่ได้เชื่อมต่อบัญชี LINE กับระบบ\n"
                                f"กรุณาไปที่เว็บไซต์เพื่อเชื่อมต่อบัญชี LINE ของคุณก่อน\n"
                                f"หลังจากเชื่อมต่อแล้ว กลับมาจองห้องใหม่อีกครั้ง"
                            )
                            is_complete = False
                        else:
                            # User found, proceed with booking
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

        # 4. อัปเดต Cache ด้วยข้อมูลที่ Python ตรวจสอบความถูกต้องแล้ว (booking_data)
        if is_complete:
            cache.delete(cache_key)
            cache.delete(state_key)
        else:
            chat_history += f"\nAI: {reply_text}"
            cache.set(cache_key, chat_history, timeout=300)
            cache.set(state_key, booking_data, timeout=300)

    except Exception as e:
        print(f"System Error: {e}", flush=True)
        traceback.print_exc()
        reply_text = f"🚨 ระบบขัดข้อง 🚨\nตัวการคือ: {str(e)}"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]
            )
        )


@login_required
def line_connect(request):
    """Generate LINE Login URL for connecting LINE account to TU account"""
    if not LINE_LOGIN_CHANNEL_ID or not LINE_LOGIN_REDIRECT_URI:
        messages.error(request, "LINE Login configuration is not set up properly.")
        return redirect("dashboard")

    # Generate a random state parameter for security
    import secrets

    state = secrets.token_urlsafe(32)

    # Store state in session for verification
    request.session["line_login_state"] = state

    # Build LINE Login URL
    params = {
        "response_type": "code",
        "client_id": LINE_LOGIN_CHANNEL_ID,
        "redirect_uri": LINE_LOGIN_REDIRECT_URI,
        "scope": "profile openid",
        "state": state,
        "bot_prompt": "normal",
    }

    line_login_url = f"https://access.line.me/oauth2/v2.1/authorize?{urlencode(params)}"

    return redirect(line_login_url)


def line_login_callback(request):
    """Handle LINE Login callback and link LINE account to user"""
    # Get parameters from callback
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")
    error_description = request.GET.get("error_description")

    # Handle errors
    if error:
        messages.error(request, f"LINE Login failed: {error_description or error}")
        return redirect("dashboard")

    # Verify state parameter
    if not state or state != request.session.get("line_login_state"):
        messages.error(request, "Invalid state parameter. Please try again.")
        return redirect("dashboard")

    # Clear state from session
    if "line_login_state" in request.session:
        del request.session["line_login_state"]

    if not code:
        messages.error(request, "No authorization code received from LINE.")
        return redirect("dashboard")

    # Exchange authorization code for access token
    import requests

    token_url = "https://api.line.me/oauth2/v2.1/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_LOGIN_REDIRECT_URI,
        "client_id": LINE_LOGIN_CHANNEL_ID,
        "client_secret": LINE_LOGIN_CHANNEL_SECRET,
    }

    try:
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()

        access_token = token_json.get("access_token")
        if not access_token:
            messages.error(request, "Failed to get access token from LINE.")
            return redirect("dashboard")

        # Get user profile from LINE
        profile_url = "https://api.line.me/v2/profile"
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = requests.get(profile_url, headers=headers)
        profile_json = profile_response.json()

        line_user_id = profile_json.get("userId")
        display_name = profile_json.get("displayName")

        if not line_user_id:
            messages.error(request, "Failed to get LINE User ID.")
            return redirect("dashboard")

        # Link LINE User ID to current user
        user = request.user
        user.line_user_id = line_user_id
        user.save()

        messages.success(
            request,
            f"LINE account connected successfully! "
            f"Your LINE display name: {display_name}",
        )

    except Exception as e:
        messages.error(request, f"Error connecting LINE account: {str(e)}")
        return redirect("dashboard")

    # Redirect to LINE Chatbot friend page after successful connection
    # line_chatbot_url = "https://line.me/R/ti/p/@040lofwv"
    # return redirect(line_chatbot_url)

    # Render success page instead of redirecting
    return render(request, "chat_bot/line_connect.html", {"display_name": display_name})
