import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

# ===== FIREBASE ADMIN CONFIG =====
# ⚠️ CÁCH CẤU HÌNH:
# 1. Firebase Console → Project Settings → Service accounts → Generate new private key
# 2. Tải file JSON (vd: serviceAccountKey.json) đặt vào thư mục backend/
# 3. Đặt biến môi trường GOOGLE_APPLICATION_CREDENTIALS trỏ tới file này
#    HOẶC đặt file ở backend/serviceAccountKey.json

GOOGLE_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "serviceAccountKey.json")
)

_firebase_app = None

def init_firebase():
    """Khởi tạo Firebase Admin nếu credentials tồn tại."""
    global _firebase_app
    try:
        if _firebase_app is None and os.path.exists(GOOGLE_CREDENTIALS):
            cred = credentials.Certificate(GOOGLE_CREDENTIALS)
            _firebase_app = firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin initialized")
        return _firebase_app
    except Exception as e:
        print(f"⚠️ Firebase init skipped: {e}")
        return None

def send_push_notification(fcm_tokens, title, body, data=None):
    """
    Gửi push notification qua Firebase Cloud Messaging.
    - fcm_tokens: list các FCM token của user
    - title, body: nội dung thông báo
    - data: dict dữ liệu kèm (key, url, ...)
    """
    if not fcm_tokens:
        return 0
    try:
        app = init_firebase()
        if app is None:
            print("⚠️ Firebase chưa cấu hình, bỏ qua push notification")
            return 0

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            tokens=fcm_tokens,
        )
        response = messaging.send_each_for_multicast(message)
        print(f"✅ Push sent: {response.success_count} success / {response.failure_count} failed")
        return response.success_count
    except Exception as e:
        print(f"❌ Push error: {e}")
        return 0