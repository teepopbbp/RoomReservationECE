import requests


def authenticate_tu(username, password):
    api_url = "https://api.tu.ac.th/api/v2/auth/login"  # สมมติ URL ตามมาตรฐาน TU
    app_key = "TU0c3f0f05bd75f3280f245a175e71c7220f9e09af6ac882b9b3731a1d21c8c018b5f4156daa01c81d8dbea4d6a839a831"  # คีย์ที่ได้จากกองบริการเทคโนโลยีฯ

    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json", "Application-Key": app_key}

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()  # คืนค่าข้อมูลนักศึกษา/พนักงาน
        return None
    except requests.exceptions.RequestException:
        return None
