import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Header, Request
from pymongo import ASCENDING

# --- CẤU HÌNH JWT ---
SECRET_KEY = os.environ.get("JWT_SECRET", "an-nguyen-price-comparison-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 ngày

# --- PASSWORD HASHING ---
def hash_password(password: str) -> str:
    """Băm mật khẩu bằng bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Kiểm tra mật khẩu."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# --- JWT TOKEN ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Giải mã JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn, vui lòng đăng nhập lại")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

# --- USER MODEL ---
async def get_user_by_email(db, email: str):
    """Tìm user theo email."""
    return await db.users.find_one({"email": email.lower().strip()})

async def get_user_by_id(db, user_id: str):
    """Tìm user theo _id."""
    from bson import ObjectId
    try:
        return await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

async def create_user(db, email: str, password: str, full_name: str = ""):
    """Tạo user mới."""
    user = {
        "email": email.lower().strip(),
        "password_hash": hash_password(password),
        "full_name": full_name.strip(),
        "favorites": [],  # Danh sách sản phẩm yêu thích
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(user)
    user["_id"] = result.inserted_id
    return user

def user_to_public(user) -> dict:
    """Chuyển user thành dict công khai (không có password_hash)."""
    return {
        "id": str(user["_id"]),
        "email": user.get("email", ""),
        "full_name": user.get("full_name", ""),
        "favorites": user.get("favorites", []),
        "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
    }

# --- DEPENDENCY: LẤY USER HIỆN TẠI TỪ TOKEN ---
async def get_current_user(
    request: Request,
    authorization: str = Header(None),
):
    """Lấy user hiện tại từ Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
    
    db = request.app.state.db
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    
    return user
