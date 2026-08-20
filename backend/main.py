import os
os.environ['KERAS_BACKEND'] = 'torch'
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import numpy as np
import torch
import keras
import joblib
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from collections import Counter
from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from transformers import AutoTokenizer, RobertaForSequenceClassification
import transformers.utils.import_utils as hf_import_utils
hf_import_utils.check_torch_load_is_safe = lambda: None
from contextlib import asynccontextmanager
import schema
import auth
import firebase_helper
import price_updater

# --- CẤU HÌNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDS = ["iphone", "samsung", "oppo", "xiaomi"]
LOOK_BACK = 5
ASPECT_LABELS = [
    "bảo_mật", "camera", "giá", "hiệu_năng", "hệ_điều_hành", 
    "khác", "loa_âm_thanh", "màn_hình", "pin", "thiết_kế"
]

import torch.nn as nn

class PyTorchLSTM(nn.Module):
    def __init__(self, input_size=1, hidden_1=64, hidden_2=32, output_size=1, dropout=0.2):
        super().__init__()
        self.lstm1 = nn.LSTM(input_size, hidden_1, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.lstm2 = nn.LSTM(hidden_1, hidden_2, batch_first=True)
        self.fc = nn.Linear(hidden_2, output_size)

    def forward(self, x):
        out, _ = self.lstm1(x)
        out = self.dropout(out)
        out, _ = self.lstm2(out)
        out = self.fc(out[:, -1, :])
        return out

    def predict(self, x, verbose=0):
        self.eval()
        with torch.no_grad():
            if isinstance(x, np.ndarray):
                x_tensor = torch.tensor(x, dtype=torch.float32)
            else:
                x_tensor = x
            out = self.forward(x_tensor)
            return out.cpu().numpy()

lstm_model, scaler = None, None
tokenizer, model_sent, model_aspect = None, None, None

def clean_product_name(name):
    if not name: return ""
    name = name.lower()
    # Chuẩn hóa từ viết tắt
    name = name.replace("ip ", "iphone ")
    name = name.replace("ss ", "samsung ")
    name = name.replace("điện thoại", "").strip()
    return " ".join(name.split())

def extract_model_base(name):
    name = clean_product_name(name)
    # Loại bỏ dung lượng (gb, tb)
    name = re.sub(r'\d+\s*(gb|tb)', '', name)
    # Loại bỏ các từ bổ trợ không phải là model chính
    junk_words = ["chính hãng", "vn/a", "5g", "4g", "lte", "lắp sim", "hàng nhập khẩu"]
    for word in junk_words:
        name = name.replace(word, "")
    return " ".join(name.split())

def parse_price(price):
    """Chuyển chuỗi giá VN ('29.990.000₫') thành số nguyên."""
    if not price:
        return 0
    digits = re.sub(r"[^\d]", "", str(price))
    if not digits:
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, model_sent, model_aspect
    print("🚀 Hệ thống so sánh giá An Nguyễn đang khởi động...")
    
    # Load LSTM Model tổng quát cho dự báo giá
    global lstm_model, scaler
    pth_path = os.path.join(BASE_DIR, "models", "general_lstm_best.pth")
    keras_path = os.path.join(BASE_DIR, "models", "general_lstm_best.keras")
    s_path = os.path.join(BASE_DIR, "models", "general_scaler.pkl")

    if os.path.exists(pth_path):
        try:
            m = PyTorchLSTM()
            m.load_state_dict(torch.load(pth_path, map_location='cpu'))
            m.eval()
            lstm_model = m
            print(f"✅ PyTorch LSTM Model loaded: {pth_path}")
        except Exception as e:
            print(f"⚠️ Không thể nạp PyTorch LSTM: {e}")
    elif os.path.exists(keras_path):
        try:
            lstm_model = keras.models.load_model(keras_path)
            print(f"✅ Keras LSTM Model loaded: {keras_path}")
        except Exception as e:
            print(f"⚠️ Không thể nạp Keras LSTM: {e}")

    if os.path.exists(s_path):
        scaler = joblib.load(s_path)
        print(f"✅ Scaler loaded: {s_path}")
    
    # Load PhoBERT Models cho NLP
    try:
        sent_path = os.path.join(BASE_DIR, "phobert_models", "sentiment_classification", "final_model")
        asp_path = os.path.join(BASE_DIR, "phobert_models", "aspect_classification", "final_model")
        
        # Đảm bảo path tồn tại
        if not os.path.exists(sent_path):
            print(f"⚠️ Sentiment path không tồn tại: {sent_path}")
            raise FileNotFoundError(f"Không tìm thấy: {sent_path}")
        if not os.path.exists(asp_path):
            print(f"⚠️ Aspect path không tồn tại: {asp_path}")
            raise FileNotFoundError(f"Không tìm thấy: {asp_path}")
        
        print(f"📂 Loading tokenizer from: {sent_path}")
        tokenizer = AutoTokenizer.from_pretrained(sent_path, use_fast=False, local_files_only=True)
        
        print(f"📂 Loading sentiment model from: {sent_path}")
        model_sent = RobertaForSequenceClassification.from_pretrained(
            sent_path, 
            num_labels=3, 
            ignore_mismatched_sizes=True,
            local_files_only=True,
            use_safetensors=True
        )
        
        print(f"📂 Loading aspect model from: {asp_path}")
        model_aspect = RobertaForSequenceClassification.from_pretrained(
            asp_path, 
            num_labels=10, 
            ignore_mismatched_sizes=True,
            local_files_only=True,
            use_safetensors=True
        )
        
        model_sent.eval()
        model_aspect.eval()
        print("✅ AI Models Ready!")
    except Exception as e: 
        print(f"❌ AI Error: {e}")
        import traceback
        traceback.print_exc()
    # Khởi tạo Firebase Admin (nếu có credentials)
    firebase_helper.init_firebase()

    # Khởi chạy background task cập nhật giá mỗi 3 giờ để phục vụ training LSTM
    background_price_task = asyncio.create_task(price_updater.price_updater_loop(interval_hours=3))
    print("⏰ Background price updater started: will update all products every 3 hours")

    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Kết nối MongoDB
MONGO_URI = os.environ.get(
    "MONGO_URI",
    os.environ.get(
        "MONGODB_URI",
        "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
    )
)
MONGO_DB = os.environ.get("MONGO_DB", "price_tracker")
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]
app.state.db = db

# 8 sàn thương mại điện tử: tên sàn -> collection trong MongoDB
STORE_COLLECTIONS = {
    "FPT Shop": "fpt",
    "Thế Giới Di Động": "tgdd",
    "CellphoneS": "cellphones",
    "Hoàng Hà Mobile": "hoangha",
    "Di Động Việt": "didongviet",
    "Viettel Store": "viettelstore",
    "Clickbuy": "clickbuy",
    "MobileCity": "mobilecity",
}

def analyze_comments_ai(comments):
    if not comments: 
        return {"pos": 0, "neu": 100, "neg": 0, "list": []}
    
    # Lấy mẫu phân tích (tối đa 10-15 câu để đảm bảo tốc độ API)
    sample = random.sample(comments, min(len(comments), 12))
    results = []
    stats = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
    
    # Từ điển từ khóa đã SẮP XẾP THEO ĐỘ DÀI (dài nhất trước) để ưu tiên cụm từ cụ thể
    aspect_keywords = [
        # CAMERA (ưu tiên cao nhất vì hay bị nhầm)
        ("camera chụp", "camera"), ("camera sau", "camera"), ("camera trước", "camera"),
        ("chụp đêm", "camera"), ("chụp ảnh", "camera"), ("chụp xóa phông", "camera"),
        ("góc siêu rộng", "camera"), ("góc rộng", "camera"), 
        ("chống rung", "camera"), ("vỡ ảnh", "camera"), ("quay phim", "camera"),
        ("quay video", "camera"), ("ống kính", "camera"), ("selfie", "camera"),
        ("xóa phông", "camera"), ("hình ảnh", "camera"), ("ảnh", "camera"),
        ("video", "camera"), ("camera", "camera"), ("chụp", "camera"),
        ("quay", "camera"), ("nét", "camera"), ("mờ", "camera"),
        ("zoom", "camera"), 
        
        # PIN
        ("dung lượng pin", "pin"), ("thời lượng pin", "pin"), ("thời gian sử dụng pin", "pin"),
        ("tụt pin nhanh", "pin"), ("tụt pin", "pin"), ("chai pin", "pin"),
        ("sạc không dây", "pin"), ("sạc nhanh", "pin"), ("sạc pin", "pin"),
        ("pin yếu", "pin"), ("pin trâu", "pin"), ("hết pin", "pin"), ("cắm sạc", "pin"),
        ("dung lượng", "pin"), ("mah", "pin"), ("pin", "pin"),
        
        # MÀN HÌNH
        ("tần số quét", "màn_hình"), ("độ phân giải màn", "màn_hình"),
        ("màn hình", "màn_hình"), ("màn cong", "màn_hình"), 
        ("tai thỏ", "màn_hình"), ("đục lỗ", "màn_hình"),
        ("hiển thị", "màn_hình"), ("oled", "màn_hình"), ("amoled", "màn_hình"),
        ("độ sáng", "màn_hình"), ("màu sắc", "màn_hình"), ("sắc nét", "màn_hình"),
        ("độ phân giải", "màn_hình"), ("cảm ứng", "màn_hình"), ("màn", "màn_hình"),
        
        # GIÁ
        ("giảm giá", "giá"), ("trả góp", "giá"), ("khuyến mãi", "giá"),
        ("giá cả", "giá"), ("đáng tiền", "giá"), ("giá", "giá"),
        ("tiền", "giá"), ("rẻ", "giá"), ("đắt", "giá"), 
        ("hợp lý", "giá"), ("sale", "giá"), ("bù", "giá"),
        ("trả trước", "giá"),
        
        # THIẾT KẾ
        ("thiết kế", "thiết_kế"), ("ngoại hình", "thiết_kế"), 
        ("chất liệu", "thiết_kế"), ("hoàn thiện", "thiết_kế"),
        ("vỏ", "thiết_kế"), ("tróc", "thiết_kế"), ("cầm", "thiết_kế"),
        ("mỏng", "thiết_kế"), ("nhẹ", "thiết_kế"), ("sang trọng", "thiết_kế"),
        ("sang", "thiết_kế"), ("đẹp", "thiết_kế"), 
        ("màu sắc", "thiết_kế"), ("màu", "thiết_kế"),
        
        # HIỆU NĂNG
        ("hiệu năng", "hiệu_năng"), ("đa nhiệm", "hiệu_năng"),
        ("nóng máy", "hiệu_năng"), ("chơi game nặng", "hiệu_năng"),
        ("chơi game", "hiệu_năng"), ("chiến game", "hiệu_năng"),
        ("mượt", "hiệu_năng"), ("lag", "hiệu_năng"), ("giật", "hiệu_năng"),
        ("fps", "hiệu_năng"), ("chip", "hiệu_năng"), ("ram", "hiệu_năng"),
        ("tốc độ", "hiệu_năng"), ("nhanh", "hiệu_năng"), ("chậm", "hiệu_năng"),
        ("đơ", "hiệu_năng"), ("xử lý", "hiệu_năng"), ("app", "hiệu_năng"),
        ("phần mềm", "hiệu_năng"), ("nóng", "hiệu_năng"),
        
        # LOA ÂM THANH - để sau cùng vì "loa" dễ match nhầm
        ("âm bass", "loa_âm_thanh"), ("âm thanh", "loa_âm_thanh"),
        ("loa ngoài", "loa_âm_thanh"), ("loa trong", "loa_âm_thanh"),
        ("nghe gọi", "loa_âm_thanh"), ("gọi điện", "loa_âm_thanh"),
        ("nghe nhạc", "loa_âm_thanh"), ("micro", "loa_âm_thanh"),
        ("mic", "loa_âm_thanh"), ("rè", "loa_âm_thanh"), ("loa", "loa_âm_thanh"),
        ("volume", "loa_âm_thanh"), ("nghe", "loa_âm_thanh"),
        
        # BẢO MẬT
        ("nhận diện khuôn mặt", "bảo_mật"), ("mở khóa khuôn mặt", "bảo_mật"),
        ("face id", "bảo_mật"), ("faceid", "bảo_mật"),
        ("vân tay", "bảo_mật"), ("mật khẩu", "bảo_mật"),
        ("khóa máy", "bảo_mật"), ("bảo mật", "bảo_mật"), ("mở khóa", "bảo_mật"),
        
        # HỆ ĐIỀU HÀNH
        ("hệ điều hành", "hệ_điều_hành"), ("bản cập nhật", "hệ_điều_hành"),
        ("cập nhật phần mềm", "hệ_điều_hành"), ("giao diện người dùng", "hệ_điều_hành"),
        ("ios", "hệ_điều_hành"), ("android", "hệ_điều_hành"), ("update", "hệ_điều_hành"),
        ("giao diện", "hệ_điều_hành")
    ]

    for text in sample:
        try:
            text_str = str(text).strip()
            text_low = text_str.lower()
            
            # 1. Dự đoán bằng Model PhoBERT (backup)
            inputs = tokenizer(text_str, return_tensors="pt", truncation=True, max_length=128, padding='max_length')
            with torch.no_grad():
                s_idx = torch.argmax(model_sent(**inputs).logits).item()
                a_idx = torch.argmax(model_aspect(**inputs).logits).item()

            # 2. Xử lý SENTIMENT
            # PhoBERT: 0: Positive, 1: Neutral, 2: Negative (từ train_phobert.py)
            label = "NEUTRAL"
            if s_idx == 0: label = "POSITIVE"
            elif s_idx == 2: label = "NEGATIVE"

            # Rule-based SENTIMENT (ưu tiên cao)
            question_words = ["không ạ", "không nhỉ", "có không", "bao nhiêu", "thế nào", 
                              "khi nào", "tư vấn", "hỏi", "còn không", "còn hàng không", 
                              "còn k ạ", "shop còn", "có hàng không"]
            
            # Negative cực kỳ mạnh - phát hiện context tiêu cực
            strong_negative = ["hỏng", "lỗi", "tệ", "kém", "thất vọng", "lừa đảo", 
                              "hư", "trả hàng", "vỡ ảnh", "treo máy", "tắt nguồn",
                              "crash", "bug", "mờ", "nóng quá", "chậm", "đơ", "lag"]
            
            negative_words = ["đắt quá", "kém chất lượng", "tụt pin nhanh", "chai pin",
                            "giật lag", "rè", "hết pin nhanh"]
            
            positive_words = ["rất tốt", "cực tốt", "quá tốt", "đáng mua", "hài lòng", 
                            "ưng ý", "chất lượng", "mượt", "ổn định",
                            "pin trâu", "sắc nét", "sang trọng", "rõ nét", "ngon"]
            
            # Kiểm tra negative trước (ưu tiên cao nhất)
            has_negative = any(n in text_low for n in strong_negative + negative_words)
            # Kiểm tra positive
            has_positive = any(p in text_low for p in positive_words)
            # Kiểm tra hỏi
            is_question = any(q in text_low for q in question_words)
            
            if is_question:
                label = "NEUTRAL"
            elif has_negative:
                label = "NEGATIVE"
            elif has_positive:
                label = "POSITIVE"
            # Nếu không khớp rule nào thì giữ lại kết quả PhoBERT

            # 3. Xử lý ASPECT - RULE-BASED ƯU TIÊN TUYỆT ĐỐI
            final_aspect = "khác"
            
            # Tìm từ khóa dài nhất match trước (đã sắp xếp theo độ dài)
            for keyword, aspect in aspect_keywords:
                if keyword in text_low:
                    final_aspect = aspect
                    break  # Chỉ lấy keyword đầu tiên match (đã sắp xếp theo độ dài)
            
            # Nếu không tìm thấy thì fallback sang PhoBERT
            if final_aspect == "khác" and a_idx < len(ASPECT_LABELS):
                final_aspect = ASPECT_LABELS[a_idx]

            stats[label] += 1
            results.append({"text": text_str, "label": label, "aspect": final_aspect})
        except:
            continue
        
    total = len(results)
    pos_count = stats["POSITIVE"]
    neg_count = stats["NEGATIVE"]
    neu_count = stats["NEUTRAL"]
    return {
        "pos": round((pos_count / total) * 100),
        "neu": round((neu_count / total) * 100),
        "neg": round((neg_count / total) * 100),
        "list": results
    }

# ============================================================
# CÁC HÀM TÍNH TOÁN NÂNG CAO (THEO GÓP Ý GIẢNG VIÊN)
# ============================================================

def calculate_pqs(product, sentiment_stats):
    """
    PQS = Product Quality Score (Thang điểm 100)
    Thành phần:
    - Rating trung bình: 25%
    - Sentiment Score: 30%
    - Uy tín gian hàng: 15%
    - Số lượng bán: 15%
    - Tỷ lệ phản hồi tích cực: 15%
    """
    # Rating: 0-5 -> quy đổi 0-100
    rating = product.get('rating', 0) or 0
    try:
        rating_score = (float(rating) / 5) * 100 if rating else 50
    except:
        rating_score = 50
    
    # Sentiment Score: % tích cực
    sentiment_score = sentiment_stats.get('pos', 0) or 0
    
    # Uy tín gian hàng (mặc định 70 nếu không có dữ liệu)
    shop_reputation = product.get('shop_reputation', 70) or 70
    
    # Số lượng bán: normalize (giả định 1000+ = 100 điểm)
    sold = product.get('sold', 0) or 0
    try:
        sold_score = min(100, (float(sold) / 1000) * 100) if sold else 50
    except:
        sold_score = 50
    
    # Tỷ lệ phản hồi tích cực
    positive_rate = sentiment_stats.get('pos', 0) or 0
    
    pqs = (rating_score * 0.25 + sentiment_score * 0.30 +
           shop_reputation * 0.15 + sold_score * 0.15 +
           positive_rate * 0.15)
    return round(pqs)


def get_pqs_label(pqs):
    """Đánh giá chất lượng dựa trên PQS"""
    if pqs >= 85:
        return {"label": "🟢 Chất lượng rất tốt", "color": "green"}
    elif pqs >= 70:
        return {"label": "🟡 Chất lượng tốt", "color": "yellow"}
    elif pqs >= 50:
        return {"label": "🟠 Chất lượng trung bình", "color": "orange"}
    else:
        return {"label": "🔴 Chất lượng kém", "color": "red"}


def calculate_price_stats(price_history):
    """
    Tính toán thống kê giá:
    - Min Price (giá thấp nhất)
    - Average Price (giá trung bình)
    - Max Price (giá cao nhất)
    - Current Price (giá hiện tại)
    """
    prices = [parse_price(h.get('price', '')) for h in price_history if h.get('price')]
    prices = [p for p in prices if p > 0]
    if not prices:
        return None
    return {
        "min": int(min(prices)),
        "avg": int(sum(prices) / len(prices)),
        "max": int(max(prices)),
        "current": int(prices[-1])
    }


def get_price_trend(current_price, forecast_price):
    """
    Xác định ranh giới tăng/giảm giá:
    - Giảm mạnh: >= 5%
    - Giảm nhẹ: 1% - 5%
    - Ổn định: ±1%
    - Tăng nhẹ: 1% - 5%
    - Tăng mạnh: >= 5%
    """
    if not current_price or not forecast_price:
        return {"trend": "Ổn định", "change_percent": 0, "icon": "➡️"}
    change = (forecast_price - current_price) / current_price * 100
    if change <= -5:
        return {"trend": "Giảm mạnh", "change_percent": round(change, 2), "icon": "📉📉"}
    elif change < -1:
        return {"trend": "Giảm nhẹ", "change_percent": round(change, 2), "icon": "📉"}
    elif change <= 1:
        return {"trend": "Ổn định", "change_percent": round(change, 2), "icon": "➡️"}
    elif change < 5:
        return {"trend": "Tăng nhẹ", "change_percent": round(change, 2), "icon": "📈"}
    else:
        return {"trend": "Tăng mạnh", "change_percent": round(change, 2), "icon": "📈📈"}


def get_buy_recommendation(pqs, price_stats, current_price, forecast_price):
    """
    Buy Recommendation Engine:
    - Nên mua ngay: Giá thấp + PQS cao + Dự báo tăng
    - Nên chờ: Giá cao + Dự báo giảm
    - Không khuyến nghị: PQS thấp + Bình luận tiêu cực nhiều
    """
    if pqs < 50:
        return {
            "action": "Không khuyến nghị",
            "reason": "Chất lượng sản phẩm thấp (PQS < 50)",
            "color": "red",
            "icon": "⛔"
        }
    
    if price_stats and current_price:
        # Giá hiện tại thấp hơn trung bình >= 5% và dự báo tăng -> Nên mua ngay
        if current_price < price_stats['avg'] * 0.95 and forecast_price > current_price:
            return {
                "action": "Nên mua ngay",
                "reason": f"Giá thấp hơn trung bình {round((1 - current_price/price_stats['avg'])*100, 1)}% và dự báo tăng giá",
                "color": "green",
                "icon": "✅"
            }
        # Giá hiện tại thấp hơn trung bình -> Nên mua
        if current_price < price_stats['avg']:
            return {
                "action": "Nên mua",
                "reason": f"Giá hiện tại thấp hơn giá trung bình ({current_price:,}đ < {price_stats['avg']:,}đ)",
                "color": "green",
                "icon": "🛒"
            }
    
    # Dự báo giảm -> Nên chờ
    if forecast_price and current_price and forecast_price < current_price:
        return {
            "action": "Nên chờ",
            "reason": f"Dự báo giá sẽ giảm {round((current_price - forecast_price)/current_price*100, 1)}%",
            "color": "yellow",
            "icon": "⏳"
        }
    
    return {
        "action": "Cân nhắc",
        "reason": "Giá hiện tại cao hơn mức trung bình, có thể chờ đợt giảm giá",
        "color": "orange",
        "icon": "🤔"
    }


def calculate_lstm_metrics(price_history, forecast_price, lstm_model=None, scaler=None, look_back=LOOK_BACK):
    """
    Đánh giá độ chính xác của LSTM bằng backtest trên dữ liệu lịch sử thực tế:
    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Square Error)
    - MAPE (Mean Absolute Percentage Error)
    - Direction Accuracy (Tỷ lệ dự báo đúng hướng)
    - accuracy: Phần trăm dự đoán giá tương lai so với giá thực tế (100 - MAPE)
    """
    prices = [parse_price(h.get('price', '')) for h in price_history if h.get('price')]
    prices = [p for p in prices if p > 0]
    if len(prices) < 3:
        return None

    # Nếu có LSTM model + scaler -> sử dụng model thật để backtest (dự báo từng bước)
    # Ngược lại -> fallback naive baseline (giá hôm trước)
    use_lstm = lstm_model is not None and scaler is not None and len(prices) > look_back

    actual = []
    predicted = []

    if use_lstm:
        # Backtest: với mỗi cửa sổ look_back, dùng LSTM dự báo giá tiếp theo (off-by-one)
        for i in range(look_back, len(prices)):
            window = prices[i - look_back:i]  # đầu vào look_back giá trước
            true_next = prices[i]              # giá thực tế ngày tiếp theo
            try:
                X_input = np.array(window).reshape(-1, 1)
                X_scaled = scaler.transform(X_input)
                pred_scaled = lstm_model.predict(X_scaled.reshape(1, look_back, 1), verbose=0)
                pred_price = int(scaler.inverse_transform(pred_scaled)[0][0])
                if pred_price > 0:
                    actual.append(true_next)
                    predicted.append(pred_price)
            except Exception:
                continue
    else:
        # Fallback: naive baseline nếu không có model
        actual = prices[1:]
        predicted = prices[:-1]

    if not actual or len(actual) < 1:
        return None

    errors = [abs(a - p) for a, p in zip(actual, predicted)]
    mae = sum(errors) / len(errors)
    rmse = (sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)) ** 0.5
    mape_values = [abs((a - p) / a) * 100 for a, p in zip(actual, predicted) if a != 0]
    mape = sum(mape_values) / len(mape_values) if mape_values else 0

    # Direction Accuracy: so sánh hướng thay đổi giữa thực tế và dự báo
    correct_direction = 0
    total_direction = 0
    for i in range(1, len(actual)):
        actual_change = actual[i] - actual[i - 1]
        predicted_change = predicted[i] - predicted[i - 1]
        if actual_change != 0:
            total_direction += 1
            if (actual_change > 0 and predicted_change > 0) or \
               (actual_change < 0 and predicted_change < 0) or \
               (abs(actual_change) < 0.01 * actual[i] and abs(predicted_change) < 0.01 * actual[i]):
                correct_direction += 1

    direction_accuracy = (correct_direction / total_direction * 100) if total_direction else 0
    # Độ chính xác dự báo giá tương lai so với giá thực tế
    accuracy = max(0.0, 100 - mape)

    return {
        "mae": round(mae),
        "rmse": round(rmse),
        "mape": round(mape, 2),
        "accuracy": round(accuracy, 1),
        "direction_accuracy": round(direction_accuracy, 1),
        "sample_size": len(actual),
        "eval_method": "lstm_backtest" if use_lstm else "naive"
    }


def calculate_rqs(comment_text, sentiment_label):
    """
    RQS = Review Quality Score (Thang 5)
    Thành phần:
    - Sentiment Score
    - Độ dài bình luận
    - Mức độ hữu ích (giả định)
    """
    if not comment_text:
        return 0
    
    text = str(comment_text).strip()
    length = len(text)
    
    # Điểm sentiment cơ bản
    if sentiment_label == "POSITIVE":
        sent_score = 4.0
    elif sentiment_label == "NEGATIVE":
        sent_score = 2.0
    else:
        sent_score = 3.0
    
    # Điểm độ dài: bình luận càng dài càng chi tiết
    if length >= 100:
        length_score = 1.0
    elif length >= 50:
        length_score = 0.7
    elif length >= 20:
        length_score = 0.4
    else:
        length_score = 0.1  # Bình luận ngắn như "Ok" -> điểm thấp
    
    rqs = min(5.0, sent_score + length_score)
    return round(rqs, 1)

@app.get("/api/search")
async def search_products(brand: str = "iphone", name: str = Query(...)):
    """
    Search Fallback Engine:
    Bước 1: Tìm kiếm sản phẩm theo TÊN trên 8 sàn trong MongoDB
    Bước 2: Nếu không tồn tại -> Trả về thông báo + gợi ý sản phẩm tương tự
    """
    search_name = clean_product_name(name)
    
    async def get_candidates(collection_name):
        col = db[collection_name]
        cursor = col.find({"name": {"$regex": search_name.replace(" ", ".*"), "$options": "i"}}).limit(20)
        return await cursor.to_list(length=20)
    
    raw_data = await asyncio.gather(*(get_candidates(c) for c in STORE_COLLECTIONS.values()))
    all_candidates = [p for sublist in raw_data for p in sublist]
    
    if not all_candidates:
        # ===== SEARCH FALLBACK ENGINE =====
        # Không có dữ liệu -> Tìm sản phẩm gợi ý cùng brand
        suggestions = []
        for source, collection_name in STORE_COLLECTIONS.items():
            col = db[collection_name]
            try:
                cursor = col.find({}).sort("last_scraped_at", -1).limit(5)
                items = await cursor.to_list(length=5)
                for item in items:
                    suggestions.append({
                        "platform": source,
                        "name": item.get('name'),
                        "current_price": parse_price(item.get('price')),
                        "image": item.get('image_url', ''),
                        "link": item.get('product_url', '#')
                    })
            except Exception:
                continue
        
        return {
            "found": False,
            "message": f"Không tìm thấy sản phẩm '{name}' trong hệ thống.",
            "search_term": name,
            "suggestions": suggestions[:10]
        }
    
    return {
        "found": True,
        "search_term": name,
        "result_count": len(all_candidates),
        "message": f"Tìm thấy {len(all_candidates)} sản phẩm cho '{name}' trên 8 sàn"
    }


@app.get("/api/compare")
async def get_comparison(brand: str = "iphone", name: str = Query(...)):
    # Chuẩn hóa tên tìm kiếm
    search_name = clean_product_name(name)
    base_search_name = extract_model_base(name)

    async def get_candidates(collection_name):
        col = db[collection_name]
        # Tìm kiếm mở rộng hơn một chút để lọc sau
        cursor = col.find({"name": {"$regex": search_name.replace(" ", ".*"), "$options": "i"}}).limit(20)
        return await cursor.to_list(length=20)

    raw_data = await asyncio.gather(*(get_candidates(c) for c in STORE_COLLECTIONS.values()))
    for i, source in enumerate(STORE_COLLECTIONS.keys()):
        print(f"DEBUG: Platform {source} found {len(raw_data[i])} items")

    # Logic Matching:
    # 1. Tìm sản phẩm có model base khớp chính xác nhất với model base của từ khóa tìm kiếm
    # 2. Nếu nhiều sản phẩm khớp model base, chọn cái phổ biến nhất hoặc khớp search_name nhất
    
    all_candidates = [p for sublist in raw_data for p in sublist]
    if not all_candidates:
        return {"results": []}

    # Tính điểm cho từng ứng viên
    scored_candidates = []
    for p in all_candidates:
        p_name = p.get('name', '')
        p_clean = clean_product_name(p_name)
        p_base = extract_model_base(p_name)
        
        score = 0
        # Ưu tiên khớp model base chính xác (vd: "iphone 12" == "iphone 12")
        if p_base == base_search_name:
            score += 100
        elif base_search_name in p_base:
            score += 50
            
        # Ưu tiên khớp toàn bộ search name (vd: "iphone 12 128gb")
        if search_name == p_clean:
            score += 30
            
        scored_candidates.append((score, p_base, p))

    # Sắp xếp theo điểm và lấy model base tốt nhất
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    best_model_base = scored_candidates[0][1] if scored_candidates else base_search_name

    # Sử dụng ngày hiện tại từ hệ thống để làm mốc đồng bộ cho cả 8 sàn
    today = datetime.now()
    # Tạo danh sách 7 ngày: [T-6, T-5, T-4, T-3, T-2, T-1, T]
    master_date_list = [(today - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(6, -1, -1)]
    # Nhãn hiển thị trên biểu đồ (ví dụ: 12/04, 13/04...)
    display_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in master_date_list]

    # Với mỗi sàn, chọn sản phẩm rẻ nhất khớp model base
    store_results = []
    for i, (source, collection_name) in enumerate(STORE_COLLECTIONS.items()):
        candidates = raw_data[i]
        platform_candidates = []
        for p in candidates:
            p_name_clean = clean_product_name(p.get('name', ''))
            p_base = extract_model_base(p_name_clean)
            
            if best_model_base in p_base or p_base in best_model_base:
                sub_score = 0
                if p_base == best_model_base: sub_score += 10
                if search_name in p_name_clean: sub_score += 5
                platform_candidates.append((sub_score, p))
        
        if not platform_candidates:
            continue
        
        platform_candidates.sort(key=lambda x: x[0], reverse=True)
        # Chọn sản phẩm rẻ nhất trong các ứng viên khớp model
        best_candidates = [p for _, p in platform_candidates]
        best_candidates.sort(key=lambda p: parse_price(p.get('price', '')))
        target_product = best_candidates[0]

        if target_product:
            p = target_product
            
            # --- BƯỚC 2: LOGIC BÙ GIÁ (FORWARD FILL) ---
            # Chuyển lịch sử từ DB thành dict để lookup: { "2026-04-18": 12490000 }
            history_dict = {}
            for h in p.get('price_history', []):
                if h.get('scraped_at'):
                    date_str = h['scraped_at'].strftime("%Y-%m-%d") if hasattr(h['scraped_at'], 'strftime') else str(h['scraped_at'])[:10]
                    history_dict[date_str] = parse_price(h.get('price', ''))
            
            final_prices = []
            # Lấy giá hiện tại làm giá mặc định khởi đầu nếu ngày đầu tiên trong chuỗi bị thiếu
            last_known_price = parse_price(p.get('price', ''))
            
            # Sắp xếp lịch sử để tìm giá thực tế cũ nhất có thể
            sorted_history_dates = sorted(history_dict.keys())
            if sorted_history_dates:
                last_known_price = history_dict[sorted_history_dates[0]]

            # Duyệt qua khung ngày chuẩn, nếu thiếu ngày nào thì lấy giá ngày trước đó
            for d_str in master_date_list:
                if d_str in history_dict:
                    last_known_price = history_dict[d_str]
                final_prices.append(last_known_price)

            # --- BƯỚC 3: DỰ BÁO GIÁ BẰNG LSTM (Model tổng quát) ---
            forecast = 0
            if lstm_model is not None and scaler is not None and final_prices:
                try:
                    # Sử dụng chuỗi giá đã được làm sạch và bù đắp để dự báo
                    # Đảm bảo đủ độ dài LOOK_BACK bằng cách padding nếu cần
                    input_prices = final_prices
                    if len(input_prices) < LOOK_BACK:
                        input_prices = [input_prices[0]] * (LOOK_BACK - len(input_prices)) + input_prices
                    
                    X_input = np.array(input_prices[-LOOK_BACK:]).reshape(-1, 1)
                    X_scaled = scaler.transform(X_input)
                    pred = lstm_model.predict(X_scaled.reshape(1, LOOK_BACK, 1), verbose=0)
                    forecast = int(scaler.inverse_transform(pred)[0][0])
                except Exception as e:
                    print(f"Lỗi dự báo {source}: {e}")

            # --- BƯỚC 4: ĐÓNG GÓI KẾT QUẢ ---
            current_price = parse_price(p.get('price', ''))
            forecast_price = forecast or current_price
            sentiment_data = analyze_comments_ai(p.get('comments', []))
            
            # Tính PQS (Product Quality Score)
            pqs = calculate_pqs(p, sentiment_data)
            pqs_label = get_pqs_label(pqs)
            
            # Tính thống kê giá (Min, Avg, Max, Current)
            price_stats = calculate_price_stats(p.get('price_history', []))
            
            # Xác định xu hướng giá
            price_trend = get_price_trend(current_price, forecast_price)
            
            # Buy Recommendation Engine
            buy_recommendation = get_buy_recommendation(pqs, price_stats, current_price, forecast_price)
            
            # LSTM Metrics (MAE, RMSE, MAPE, Direction Accuracy, Accuracy %)
            lstm_metrics = calculate_lstm_metrics(p.get('price_history', []), forecast_price, lstm_model, scaler)
            
            # Thêm RQS cho từng comment
            sentiment_list = sentiment_data.get('list', [])
            for cmt in sentiment_list:
                cmt['rqs'] = calculate_rqs(cmt.get('text', ''), cmt.get('label', 'NEUTRAL'))
            
            store_results.append({
                "platform": source,
                "name": p.get('name'),
                "current_price": current_price,
                "forecast": forecast_price,
                "last_crawl_date": sorted_history_dates[-1] if sorted_history_dates else "N/A",
                "image": p.get('image_url', ''),
                "sentiment": sentiment_data,
                "chart": {
                    "labels": display_labels, # Luôn dùng chung 1 trục ngày
                    "data": final_prices      # Luôn trả về đủ 7 điểm dữ liệu
                },
                "link": p.get('product_url', '#'),
                # === CÁC CHỈ SỐ NÂNG CAO (THEO GÓP Ý GIẢNG VIÊN) ===
                "pqs": pqs,
                "pqs_label": pqs_label,
                "price_stats": price_stats,
                "price_trend": price_trend,
                "buy_recommendation": buy_recommendation,
                "lstm_metrics": lstm_metrics
            })

    # Sắp xếp theo giá tăng dần và trả về 3 sàn rẻ nhất
    store_results.sort(key=lambda r: r["current_price"] or 0)
    return {"results": store_results[:3]}


# ============================================================
# XÁC THỰC JWT - ĐĂNG KÝ / ĐĂNG NHẬP / YÊU THÍCH / THÔNG BÁO
# ============================================================

@app.post("/api/auth/register")
async def register(
    email: str = Body(...),
    password: str = Body(...),
    full_name: str = Body(""),
):
    """Đăng ký tài khoản mới bằng email."""
    if not email or "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Email không hợp lệ")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự")

    existing = await auth.get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Email đã được đăng ký")

    user = await auth.create_user(db, email, password, full_name)
    token = auth.create_access_token({"sub": str(user["_id"])})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": auth.user_to_public(user)
    }


@app.post("/api/auth/login")
async def login(
    email: str = Body(...),
    password: str = Body(...),
):
    """Đăng nhập bằng email + mật khẩu."""
    user = await auth.get_user_by_email(db, email)
    if not user or not auth.verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    token = auth.create_access_token({"sub": str(user["_id"])})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": auth.user_to_public(user)
    }


@app.get("/api/auth/me")
async def get_me(user=Depends(auth.get_current_user)):
    """Lấy thông tin user hiện tại."""
    return auth.user_to_public(user)


@app.post("/api/favorites")
async def add_favorite(
    product: dict = Body(...),
    user=Depends(auth.get_current_user),
):
    """Thêm sản phẩm vào danh sách yêu thích (cần đăng nhập)."""
    fav = {
        "platform": product.get("platform", ""),
        "name": product.get("name", ""),
        "current_price": product.get("current_price", 0),
        "forecast": product.get("forecast", 0),
        "image": product.get("image", ""),
        "link": product.get("link", "#"),
        "added_pqs": product.get("pqs", None),
        "added_at": datetime.now(timezone.utc),
    }
    if not fav["name"]:
        raise HTTPException(status_code=400, detail="Thiếu tên sản phẩm")

    # Kiểm tra trùng lặp
    for existing in user.get("favorites", []):
        if existing.get("name") == fav["name"] and existing.get("platform") == fav["platform"]:
            raise HTTPException(status_code=400, detail="Sản phẩm đã có trong danh sách yêu thích")

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$push": {"favorites": fav}}
    )
    return {"ok": True, "message": "Đã thêm vào yêu thích", "favorite": fav}


@app.get("/api/favorites")
async def get_favorites(user=Depends(auth.get_current_user)):
    """Xem danh sách sản phẩm yêu thích."""
    return {"favorites": user.get("favorites", [])}


@app.delete("/api/favorites")
async def remove_favorite(
    name: str = Query(...),
    platform: str = Query(...),
    user=Depends(auth.get_current_user),
):
    """Xóa sản phẩm khỏi danh sách yêu thích."""
    result = await db.users.update_one(
        {"_id": user["_id"]},
        {"$pull": {"favorites": {"name": name, "platform": platform}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm yêu thích")
    return {"ok": True, "message": "Đã xóa khỏi yêu thích"}


@app.get("/api/notifications")
async def get_notifications(user=Depends(auth.get_current_user)):
    """
    Thông báo cho sản phẩm yêu thích - In-App Notification Engine:
    - Giá giảm so với lúc thêm vào
    - Giá giảm sâu (>= 10%)
    - Giá thấp hơn trung bình
    - Dự báo sắp tăng giá (nên mua ngay)
    - Chất lượng sản phẩm tăng (PQS)
    - Xuất hiện nhiều bình luận tiêu cực
    """
    notifications = []
    favorites = user.get("favorites", [])
    seen_keys = set()

    # Lấy thông báo đã lưu trong DB (đã đọc flags) để hợp nhất trạng thái
    saved_notifs = {}
    try:
        notif_col = db.notifications
        cursor = notif_col.find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(50)
        saved_list = await cursor.to_list(length=50)
        for n in saved_list:
            key = n.get("key", "")
            saved_notifs[key] = n.get("read", False)
    except Exception:
        saved_list = []

    now = datetime.now(timezone.utc)

    async def find_latest_product(fav):
        """Tìm sản phẩm và lịch sử giá mới nhất từ DB."""
        col_name = STORE_COLLECTIONS.get(fav.get("platform", ""))
        if not col_name:
            return None
        try:
            col = db[col_name]
            cursor = col.find({"name": {"$regex": re.escape(fav.get("name", "")), "$options": "i"}}).limit(3)
            items = await cursor.to_list(length=3)
            if not items:
                return None
            # Ưu tiên sản phẩm có price_history phong phú
            items.sort(key=lambda x: len(x.get("price_history", []) or []), reverse=True)
            return items[0]
        except Exception:
            return None

    for fav in favorites:
        fav_name = fav.get("name", "")
        fav_platform = fav.get("platform", "")
        added_price = fav.get("current_price", 0)
        added_pqs = fav.get("added_pqs", None)
        added_forecast = fav.get("forecast", 0)

        product = await find_latest_product(fav)
        if not product:
            continue

        current_price = parse_price(product.get("price", "")) or added_price

        # Tính lại các chỉ số cho sản phẩm hiện tại
        sentiment_data = analyze_comments_ai(product.get("comments", []))
        current_pqs = calculate_pqs(product, sentiment_data)
        price_stats = calculate_price_stats(product.get("price_history", []))
        price_trend = get_price_trend(current_price, product.get("forecast", 0) or 0)
        forecast_price = (product.get("forecast") or 0) or current_price

        # ===== 1. GIÁ GIẢM SO VỚI LÚC THÊM =====
        if current_price and added_price and current_price < added_price:
            drop_pct = round((added_price - current_price) / added_price * 100, 1)
            key = f"drop_{fav_platform}_{fav_name}_{round(current_price)}"
            if key not in seen_keys:
                seen_keys.add(key)
                read = saved_notifs.get(key, False)
                notifications.append({
                    "key": key,
                    "read": read,
                    "type": "price_drop",
                    "icon": "📉",
                    "title": "Giá đã giảm",
                    "message": f"{fav_name} giảm {drop_pct}% (từ {added_price:,}đ xuống {current_price:,}đ)",
                    "product": fav,
                    "current_price": current_price,
                    "created_at": now.isoformat(),
                })

            # ===== 2. GIÁ GIẢM SÂU (>= 10%) =====
            if drop_pct >= 10:
                key = f"deep_{fav_platform}_{fav_name}_{round(current_price)}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    read = saved_notifs.get(key, False)
                    notifications.append({
                        "key": key,
                        "read": read,
                        "type": "deep_drop",
                        "icon": "🚨",
                        "title": "Giá giảm sâu",
                        "message": f"🔥 {fav_name} giảm tới {drop_pct}% — cơ hội mua giá tốt!",
                        "product": fav,
                        "current_price": current_price,
                        "created_at": now.isoformat(),
                    })

        # ===== 3. GIÁ THẤP HƠN TRUNG BÌNH =====
        if price_stats and current_price and current_price < price_stats.get('avg', 0):
            below_pct = round((1 - current_price / price_stats['avg']) * 100, 1)
            if below_pct >= 3:
                key = f"avg_{fav_platform}_{fav_name}_{round(current_price)}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    read = saved_notifs.get(key, False)
                    notifications.append({
                        "key": key,
                        "read": read,
                        "type": "below_avg",
                        "icon": "💯",
                        "title": "Giá thấp hơn trung bình",
                        "message": f"{fav_name} đang thấp hơn giá trung bình {below_pct}% — đáng cân nhắc mua",
                        "product": fav,
                        "current_price": current_price,
                        "avg_price": price_stats['avg'],
                        "created_at": now.isoformat(),
                    })

        # ===== 4. DỰ BÁO SẮP TĂNG GIÁ (nên mua ngay) =====
        if forecast_price and current_price and forecast_price > current_price:
            up_pct = round((forecast_price - current_price) / current_price * 100, 1)
            if up_pct >= 2:
                key = f"up_{fav_platform}_{fav_name}_{round(forecast_price)}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    read = saved_notifs.get(key, False)
                    notifications.append({
                        "key": key,
                        "read": read,
                        "type": "forecast_up",
                        "icon": "📈",
                        "title": "Dự báo sắp tăng giá",
                        "message": f"{fav_name} dự báo tăng {up_pct}% lên {forecast_price:,}đ — nên mua ngay!",
                        "product": fav,
                        "current_price": current_price,
                        "forecast_price": forecast_price,
                        "created_at": now.isoformat(),
                    })

        # ===== 5. CHẤT LƯỢNG SẢN PHẨM TĂNG =====
        if added_pqs and current_pqs and current_pqs > added_pqs:
            pqs_diff = current_pqs - added_pqs
            if pqs_diff >= 5:
                key = f"pqs_{fav_platform}_{fav_name}_{current_pqs}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    read = saved_notifs.get(key, False)
                    notifications.append({
                        "key": key,
                        "read": read,
                        "type": "pqs_up",
                        "icon": "⭐",
                        "title": "Chất lượng sản phẩm tăng",
                        "message": f"PQS của {fav_name} tăng từ {added_pqs} lên {current_pqs} — đáng tin cậy hơn",
                        "product": fav,
                        "pqs": current_pqs,
                        "created_at": now.isoformat(),
                    })

        # ===== 6. NHIỀU BÌNH LUẬN TIÊU CỰC =====
        total_comments = len(product.get("comments", []) or [])
        if total_comments >= 5 and sentiment_data.get("neg", 0) >= 40:
            neg_count = round(total_comments * sentiment_data['neg'] / 100)
            key = f"neg_{fav_platform}_{fav_name}_{current_pqs}"
            if key not in seen_keys:
                seen_keys.add(key)
                read = saved_notifs.get(key, False)
                notifications.append({
                    "key": key,
                    "read": read,
                    "type": "negative_comments",
                    "icon": "😞",
                    "title": "Nhiều bình luận tiêu cực",
                    "message": f"⚠️ {fav_name} có {neg_count}/{total_comments} bình luận tiêu cực — cân nhắc kỹ trước khi mua",
                    "product": fav,
                    "negative_pct": sentiment_data['neg'],
                    "created_at": now.isoformat(),
                })

    # Sắp xếp mới nhất trước
    notifications.sort(key=lambda n: n.get("created_at", ""), reverse=True)

    # Lưu notifications mới vào DB để theo dõi trạng thái đã đọc
    unread = [n for n in notifications if not n.get("read")]
    if unread:
        try:
            notif_col = db.notifications
            for n in unread:
                try:
                    await notif_col.update_one(
                        {"user_id": str(user["_id"]), "key": n.get("key")},
                        {"$setOnInsert": {
                            "user_id": str(user["_id"]),
                            "key": n.get("key"),
                            "type": n.get("type"),
                            "title": n.get("title"),
                            "message": n.get("message"),
                            "product": n.get("product"),
                            "created_at": now,
                            "read": False,
                        }},
                        upsert=True
                    )
                except Exception:
                    continue
        except Exception:
            pass

    # ===== FIREBASE PUSH NOTIFICATION =====
    if unread:
        try:
            fcm_tokens = user.get("fcm_tokens", [])
            if fcm_tokens:
                for n in unread[:3]:
                    firebase_helper.send_push_notification(
                        fcm_tokens,
                        title=n.get("title", "Thông báo mới"),
                        body=n.get("message", ""),
                        data={
                            "key": n.get("key", ""),
                            "type": n.get("type", ""),
                            "url": "/",
                        }
                    )
        except Exception as e:
            print(f"❌ Push notification error: {e}")

    return {"notifications": notifications}


@app.post("/api/fcm-token")
async def register_fcm_token(
    token: str = Body(..., embed=True),
    user=Depends(auth.get_current_user),
):
    """Đăng ký FCM token (Firebase Cloud Messaging) cho user để nhận push notification."""
    if not token:
        raise HTTPException(status_code=400, detail="Thiếu FCM token")
    try:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$addToSet": {"fcm_tokens": token}}
        )
        return {"ok": True, "message": "FCM token đã đăng ký"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/mark-read")
async def mark_notifications_read(
    user=Depends(auth.get_current_user),
    payload: dict = Body(default={}),
):
    """
    Đánh dấu 1 hoặc tất cả thông báo đã đọc.
    Body: {"keys": ["key1", "key2"]} hoặc {"all": true}
    """
    keys = payload.get("keys", []) if payload else []
    mark_all = (payload or {}).get("all", False)

    try:
        notif_col = db.notifications
        if mark_all:
            await notif_col.update_many(
                {"user_id": str(user["_id"])},
                {"$set": {"read": True}}
            )
        elif keys:
            await notif_col.update_many(
                {"user_id": str(user["_id"]), "key": {"$in": keys}},
                {"$set": {"read": True}}
            )
    except Exception:
        pass
    return {"ok": True}


@app.post("/api/ingest")
async def api_ingest(platform: str = Query(...), brand: str = Query(...), payload: dict = None):
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing product payload")
    if platform not in STORE_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")
    try:
        normalized = schema.normalize_product(payload, brand=brand, platform=platform)
        col_name = STORE_COLLECTIONS[platform]
        await schema.upsert_product(db, col_name, normalized)
        return {"ok": True, "stored": True, "name": normalized.get("name")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")


def require_admin(x_api_key: str = Header(None)):
    if not ADMIN_API_KEY:
        return True
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: invalid admin API key")
    return True


@app.post("/api/admin/update-prices")
async def manual_update_prices(_: bool = Depends(require_admin)):
    """Endpoint để trigger cập nhật giá thủ công (cho testing/LSTM data collection)."""
    try:
        count = await price_updater.update_prices_once()
        return {"ok": True, "updated_count": count, "message": f"Updated {count} products"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/price-stats")
async def price_stats(_: bool = Depends(require_admin)):
    """Thống kê số lượng sản phẩm và lịch sử giá trong DB."""
    db = app.state.db
    stats = {}
    total_products = 0
    total_history = 0
    for source, col_name in STORE_COLLECTIONS.items():
        col = db[col_name]
        count = await col.count_documents({})
        total_products += count
        pipeline = [
            {"$project": {"history_count": {"$size": {"$ifNull": ["$price_history", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$history_count"}}}
        ]
        agg = await col.aggregate(pipeline).to_list(length=1)
        history_count = agg[0]["total"] if agg else 0
        total_history += history_count
        stats[source] = {"products": count, "price_records": history_count}
    return {
        "total_products": total_products,
        "total_price_records": total_history,
        "per_platform": stats
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
# uvicorn main:app --reload
# python -m uvicorn main:app --reload
