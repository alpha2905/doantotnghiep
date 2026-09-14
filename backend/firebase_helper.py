import os
import sys
import json
import requests
import firebase_admin
from firebase_admin import credentials, messaging

import builtins as _builtins

def _safe_print(*args, **kwargs):
    """In log an toàn (không crash trên console cp1252 khi có emoji/unicode VN)."""
    try:
        _builtins.print(*args, **kwargs, flush=True)
    except Exception:
        try:
            text = " ".join(str(a) for a in args)
            _builtins.print(text.encode("utf-8", "replace").decode("utf-8", "replace"), flush=True)
        except Exception:
            pass

print = _safe_print  # noqa: A001 (override print cho toàn module)

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

# ===== EXPO PUSH SERVICE =====
# Mobile app (Expo) đăng ký Expo push token dạng "ExponentPushToken[...]",
# KHÔNG phải native FCM token. Token này gửi được qua Expo Push HTTP API.
EXPO_PUSH_URL = os.environ.get("EXPO_PUSH_URL", "https://exp.host/--/api/v2/push/send")
EXPO_ACCESS_TOKEN = os.environ.get("EXPO_ACCESS_TOKEN", "")

_firebase_app = None


def init_firebase():
    """Khởi tạo Firebase Admin nếu credentials tồn tại.

    Hỗ trợ 2 cách cấu hình (khớp backend/.env.example):
      1. FIREBASE_SERVICE_ACCOUNT_JSON  - nội dung JSON service account (chuỗi)
      2. GOOGLE_APPLICATION_CREDENTIALS - đường dẫn tới file serviceAccountKey.json
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    try:
        inline = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        if inline:
            _firebase_app = firebase_admin.initialize_app(
                credentials.Certificate(json.loads(inline))
            )
            _safe_print("✅ Firebase Admin initialized (FIREBASE_SERVICE_ACCOUNT_JSON)")
        elif os.path.exists(GOOGLE_CREDENTIALS):
            cred = credentials.Certificate(GOOGLE_CREDENTIALS)
            _firebase_app = firebase_admin.initialize_app(cred)
            _safe_print("✅ Firebase Admin initialized")
        return _firebase_app
    except Exception as e:
        _safe_print(f"⚠️ Firebase init skipped: {e}")
        return None


def is_expo_token(tok: str) -> bool:
    """Phân biệt Expo push token (mobile) vs native FCM token (web)."""
    return (tok or "").startswith(("ExponentPushToken[", "ExpoPushToken["))


def send_expo_push(tokens, title, body, data=None):
    """Gửi push qua Expo Push HTTP API dành cho token mobile (Expo)."""
    messages = [
        {"to": tok, "title": title, "body": body, "data": data or {},
         "sound": "default", "channelId": "default"}
        for tok in tokens
    ]
    if not messages:
        return 0
    headers = {"Content-Type": "application/json"}
    if EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {EXPO_ACCESS_TOKEN}"
    try:
        resp = requests.post(EXPO_PUSH_URL, json=messages, headers=headers, timeout=15)
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else []
        ok = [r for r in result if r.get("status") == "ok"]
        print(f"✅ Expo push sent: {len(ok)} success / {len(result) - len(ok)} failed")
        return len(ok)
    except Exception as e:
        print(f"❌ Expo push error: {e}")
        return 0


def send_push_notification(fcm_tokens, title, body, data=None):
    """
    Gửi push notification qua Firebase Cloud Messaging (web) HOẶC
    Expo Push Service (mobile), tự phát hiện loại token.
    - fcm_tokens: list các token của user (Expo hoặc FCM)
    - title, body: nội dung thông báo
    - data: dict dữ liệu kèm (key, url, ...)
    """
    if not fcm_tokens:
        return 0
    fcm_tokens = [t for t in fcm_tokens if t]

    # Tách theo loại token
    expo_tokens = [t for t in fcm_tokens if is_expo_token(t)]
    native_tokens = [t for t in fcm_tokens if not is_expo_token(t)]

    total = 0
    if expo_tokens:
        total += send_expo_push(expo_tokens, title, body, data)

    if native_tokens:
        try:
            app = init_firebase()
            if app is None:
                print("⚠️ Firebase chưa cấu hình, bỏ qua push notification (web)")
            else:
                message = messaging.MulticastMessage(
                    notification=messaging.Notification(title=title, body=body),
                    data=data or {},
                    tokens=native_tokens,
                )
                response = messaging.send_each_for_multicast(message)
                print(f"✅ Push sent: {response.success_count} success / {response.failure_count} failed")
                total += response.success_count
        except Exception as e:
            print(f"❌ Push error: {e}")
    return total