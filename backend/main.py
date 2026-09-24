import os
os.environ['KERAS_BACKEND'] = 'torch'
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import numpy as np
import torch
try:
    import keras
except Exception:
    keras = None
import joblib
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from collections import Counter
from fastapi import FastAPI, HTTPException, Query, Depends, Body, Header
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

# --- Hybrid Forecast + Comment Analyzer (module tách riêng, xem docs/REWRITE_PLAN.md) ---
import forecaster
import comment_analyzer
import json

# --- CẤU HÌNH (ưu tiên biến môi trường khi deploy) ---
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
    elif os.path.exists(keras_path) and keras is not None:
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
        sent_path = os.path.join(BASE_DIR, "model", "phobert_models", "sentiment_classification", "final_model")
        asp_path = os.path.join(BASE_DIR, "model", "phobert_models", "aspect_classification", "final_model")
        
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
    # Nạp ánh xạ nhãn của PhoBERT từ label_mapping.json (tránh bug đảo nhãn POSITIVE/NEGATIVE)
    global SENTIMENT_LABEL_MAP, ASPECT_LABEL_MAP, LABEL_MAP_SOURCES
    SENTIMENT_LABEL_MAP, ASPECT_LABEL_MAP, LABEL_MAP_SOURCES = comment_analyzer.load_label_maps(
        os.path.join(BASE_DIR, "model", "phobert_models", "sentiment_classification", "final_model"),
        os.path.join(BASE_DIR, "model", "phobert_models", "aspect_classification", "final_model"),
    )
    print(f"🏷️ Label mapping sentiment: {SENTIMENT_LABEL_MAP}")
    print(f"🏷️ Label mapping aspect: {len(ASPECT_LABEL_MAP)} nhãn | nguồn: {LABEL_MAP_SOURCES}")

    # Khởi tạo Firebase Admin (nếu có credentials)
    firebase_helper.init_firebase()

    # Khởi chạy background task cập nhật giá mỗi 3 giờ để phục vụ training LSTM
    # TẠM TẮT: chỉ chạy khi cần scrape data mới
    # background_price_task = asyncio.create_task(price_updater.price_updater_loop(interval_hours=3))
    # print("⏰ Background price updater started: will update all products every 3 hours")
    print("ℹ️ Background price updater DISABLED (run scrapers.py manually when needed)")
    
    # Khởi chạy background task phân tích bình luận theo chu kỳ
    # TẠM TẮT: chạy khi cần phân tích lại toàn bộ sản phẩm
    # from background_workers import CommentAnalysisWorker
    # worker = CommentAnalysisWorker(MONGO_URI, MONGO_DB)
    # await worker.connect()
    # background_comment_task = asyncio.create_task(worker.analyze_all_platforms(list(STORE_COLLECTIONS.keys())))
    # print("⏰ Background comment analyzer started")

    yield

app = FastAPI(lifespan=lifespan)

# CORS: local cho phép tất cả; production giới hạn theo FRONTEND_ORIGINS
# (vd: FRONTEND_ORIGINS=https://datn-2905.web.app,https://datn-2905.firebaseapp.com)
def _cors_origins() -> list:
    raw = os.environ.get("FRONTEND_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache kết quả so sánh để trả về nhanh (TTL 10 phút)
compare_cache = {}
COMPARE_CACHE_TTL = 600  # giây

# Cache AI computations để tránh chạy lại model không cần thiết
ai_cache = {}
AI_CACHE_TTL = 3600  # 1 giờ
import time as _time

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

# --- Ánh xạ nhãn PhoBERT: ĐỌC TỪ label_mapping.json của model (được set trong lifespan).
# Lý do: model fine-tune lưu thứ tự nhãn 0=negative, 1=neutral, 2=positive (xem train_phobert_from_labeled.py),
# trong khi code cũ hardcode 0=POSITIVE/2=NEGATIVE => nhãn bị ĐẢO NGƯỢC (đã sửa).
SENTIMENT_LABEL_MAP = None
ASPECT_LABEL_MAP = None
LABEL_MAP_SOURCES = {}


def analyze_comments_ai(comments, sample_limit=50):
    """Wrapper tương thích ngược: phân tích bình luận bằng hybrid PhoBERT + rule-based.

    Logic thật nằm ở comment_analyzer.analyze_comments (dùng chung với background worker).
    """
    return comment_analyzer.analyze_comments(
        comments,
        tokenizer,
        model_sent,
        model_aspect,
        sample_limit=sample_limit,
        sentiment_map=SENTIMENT_LABEL_MAP,
        aspect_map=ASPECT_LABEL_MAP,
        label_sources=LABEL_MAP_SOURCES,
    )


# ============================================================
# CÁC HÀM TÍNH TOÁN NÂNG CAO (THEO GÓP Ý GIẢNG VIÊN)
# ============================================================

def calculate_pqs(product, sentiment_stats, current_price=None, forecast_price=None, min_market_price=None, max_market_price=None, return_breakdown=False):
    """
    PQS = Product Quality Score (Thang điểm 100)
    Công thức theo đề tài:
    PQS = (S_Rating × 0.25) + (S_Sentiment × 0.30) + (S_ShopRep × 0.15) + (S_NegPenalty × 0.15) + (S_Sold × 0.15)
    
    Thay đổi: S_PosRate bị loại bỏ vì trùng lặp với S_Sentiment.
    Thay vào đó dùng S_NegPenalty để tránh điểm thấp bất thường khi thiếu dữ liệu positive.
    
    Trọng số được heuristic từ prototype, chưa được tối ưu hóa bằng khảo sát.
    Chi tiết xem backend/config/pqs_weights.yaml
    """
    # 1. S_Rating: Điểm đánh giá sao (0-100)
    rating = product.get('rating', 0) or 0
    try:
        s_rating = (float(rating) / 5.0) * 100 if rating else 50
    except:
        s_rating = 50
    
    # 2. S_Sentiment: Tỷ lệ bình luận tích cực (0-100)
    s_sentiment = sentiment_stats.get('pos', 0) or 0
    
    # 3. S_ShopRep: Uy tín cửa hàng (0-100) - heuristic
    # Cửa hàng lớn có chính sách đổi trả tốt
    platform = product.get('platform', '')
    shop_reputation_map = {
        'Thế Giới Di Động': 90, 'FPT Shop': 85, 'CellphoneS': 85,
        'Hoàng Hà Mobile': 75, 'Viettel Store': 80, 'Clickbuy': 75, 'MobileCity': 70
    }
    s_shop_rep = shop_reputation_map.get(platform, 70)
    
    # 4. S_NegPenalty: Phần thưởng/trừ dựa trên tỷ lệ bình luận tiêu cực (0-100)
    # Thay thế S_PosRate để tránh trùng lặp với S_Sentiment.
    # Công thức: 100% negative -> 0 điểm, 0% negative -> 100 điểm
    total_comments = sentiment_stats.get('total', 0) or 0
    neg_ratio = (sentiment_stats.get('neg', 0) or 0) / 100 if total_comments > 0 else 0
    s_neg_penalty = max(0, 100 - neg_ratio * 150)  # 0% neg -> 100, 33% neg -> 50, 67%+ neg -> 0
    
    # 5. S_Sold: Số lượng đã bán (0-100) - normalize log scale
    sold_volume = product.get('sold_volume', 0) or 0
    if sold_volume > 0:
        import math
        s_sold = min(100, math.log10(sold_volume + 1) * 20)  # log scale: 10->20, 100->40, 1000->60, 10000->80, 100000->100
    else:
        s_sold = 50  # mặc định nếu không có dữ liệu
    
    # Trọng số theo tài liệu đề tài
    W_RATING = 0.25
    W_SENTIMENT = 0.30
    W_SHOP_REP = 0.15
    W_NEG_PENALTY = 0.15
    W_SOLD = 0.15
    
    pqs = (s_rating * W_RATING) + (s_sentiment * W_SENTIMENT) + \
          (s_shop_rep * W_SHOP_REP) + (s_neg_penalty * W_NEG_PENALTY) + \
          (s_sold * W_SOLD)
    total = round(min(100, max(0, pqs)))

    if not return_breakdown:
        return total

    return {
        "total": total,
        "components": {
            "rating": round(s_rating, 1),
            "sentiment": round(s_sentiment, 1),
            "shop_reputation": round(s_shop_rep, 1),
            "neg_penalty": round(s_neg_penalty, 1),
            "sold_volume": round(s_sold, 1),
        },
        "weights": {
            "rating": W_RATING,
            "sentiment": W_SENTIMENT,
            "shop_reputation": W_SHOP_REP,
            "neg_penalty": W_NEG_PENALTY,
            "sold_volume": W_SOLD,
        },
        "inputs": {
            "rating": rating,
            "sentiment_pos_percent": sentiment_stats.get('pos', 0),
            "sentiment_neg_percent": sentiment_stats.get('neg', 0),
            "analyzed_comments": total_comments,
            "sold_volume": sold_volume,
            "platform": platform,
        },
        "formula": "PQS = 0.25*S_Rating + 0.30*S_Sentiment + 0.15*S_ShopRep + 0.15*S_NegPenalty + 0.15*S_Sold",
        "note": "Trọng số heuristic của prototype, chi tiết rationale xem backend/config/pqs_weights.yaml",
    }


def build_lstm_metrics_payload(forecast_info):
    """Chuyển payload của Hybrid Forecast Engine -> lstm_metrics (giữ tương thích giao diện cũ).

    LƯU Ý MINH BẠCH: các chỉ số dưới đây là của PHƯƠNG PHÁP ĐƯỢC CHỌN (có thể là baseline
    Naive/Moving-Average nếu baseline tốt hơn LSTM trên chính chuỗi giá của sản phẩm).
    Giao diện hiển thị kèm tên phương pháp để tránh hiểu nhầm là "độ chính xác LSTM".
    """
    models = forecast_info.get("models_compared") or []
    selected = next((m for m in models if m.get("selected")), None)

    base = {
        "eval_method": forecast_info.get("method"),
        "eval_protocol": forecast_info.get("eval_protocol"),
        "selected_method": forecast_info.get("method"),
        "selected_method_name": forecast_info.get("method_name"),
        "sample_size": forecast_info.get("sample_size", 0),
        "models": models,
        "note": forecast_info.get("eval_note"),
    }
    if not selected:
        return base

    mape = float(selected.get("mape") or 0)
    base.update({
        "mae": selected.get("mae"),
        "rmse": selected.get("rmse"),
        "mape": selected.get("mape"),
        "smape": selected.get("smape"),
        "direction_accuracy": selected.get("direction_accuracy"),
        "accuracy": round(max(0.0, 100 - mape), 1),
        "sample_size": selected.get("samples"),
        "selected_method": selected.get("key"),
        "selected_method_name": selected.get("name"),
    })
    return base


def get_pqs_label(pqs):
    """Đánh giá chất lượng dựa trên PQS"""
    if pqs >= 75:
        return {"label": "🟢 Chất lượng rất tốt", "color": "green"}
    elif pqs >= 60:
        return {"label": "🟡 Chất lượng tốt", "color": "yellow"}
    elif pqs >= 45:
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
    if pqs < 45:
        return {
            "action": "Không khuyến nghị",
            "reason": "Chất lượng sản phẩm thấp (PQS < 45)",
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


# (LEGACY) Giữ lại để tham chiếu/so sánh: runtime đã chuyển sang forecaster.forecast_next()
# (rolling-origin backtest cho TẤT CẢ phương pháp, không chỉ LSTM).
def calculate_lstm_metrics(price_history, forecast_price, lstm_model=None, scaler=None, look_back=LOOK_BACK):
    """
    Đánh giá độ chính xác của LSTM bằng backtest trên dữ liệu lịch sử thực tế:
    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Square Error)
    - MAPE (Mean Absolute Percentage Error)
    - Direction Accuracy (Tỷ lệ dự báo đúng hướng)
    - accuracy: Phần trăm dự đoán giá tương lai so với giá thực tế (100 - MAPE)
    """
    history_dict = {}
    for h in price_history:
        if not h:
            continue
        price_val = parse_price(h.get('price', ''))
        if price_val <= 0:
            continue
        scraped_at = h.get('scraped_at')
        if hasattr(scraped_at, 'strftime'):
            date_str = scraped_at.strftime("%Y-%m-%d")
        else:
            date_str = str(scraped_at)[:10]
        history_dict[date_str] = price_val

    if len(history_dict) < 3:
        return None

    sorted_dates = sorted(history_dict.keys())
    start_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d")
    end_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")

    prices = []
    last_price = None
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        if date_str in history_dict:
            last_price = history_dict[date_str]
        prices.append(last_price)
        current = current + timedelta(days=1)

    prices = [p for p in prices if p is not None and p > 0]
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
        "eval_method": "lstm_backtest" if use_lstm else "naive",
        "evaluation_context": "historical_test_set_evaluation",
        "note": "Các chỉ số (MAE, RMSE, MAPE) là kết quả đánh giá thực nghiệm trên dữ liệu kiểm thử lịch sử (Historical Evaluation)."
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

# Health check cho nền tảng deploy (Render/Railway) + kiểm tra nhanh local.
@app.get("/health")
async def health():
    try:
        await db.command("ping")
        mongo = "ok"
    except Exception as e:
        mongo = f"error: {e}"
    return {"status": "ok", "mongo": mongo}


@app.get("/api/search")
async def search_products(brand: str = "iphone", name: str = Query(...)):
    """
    Search Fallback Engine:
    Bước 1: Tìm kiếm sản phẩm theo TÊN trên 8 sàn trong MongoDB
    Bước 2: Nếu không tồn tại hoặc không đủ >=3 sàn -> Trả về thông báo + gợi ý sản phẩm tương tự
    """
    search_name = clean_product_name(name)
    
    async def get_candidates(collection_name):
        col = db[collection_name]
        cursor = col.find({"name": {"$regex": search_name.replace(" ", ".*"), "$options": "i"}}).limit(20)
        return await cursor.to_list(length=20)
    
    raw_data = await asyncio.gather(*(get_candidates(c) for c in STORE_COLLECTIONS.values()))
    
    # Đếm số sàn có kết quả
    platforms_with_results = sum(1 for items in raw_data if items)
    
    # Nếu không có dữ liệu HOẶC không đủ >=1 sàn -> kích hoạt fallback
    if not any(raw_data) or platforms_with_results < 1:
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
                        "image": item.get('image', '') or item.get('image_url', ''),
                        "link": item.get('product_url', '#')
                    })
            except Exception:
                continue
        
        return {
            "found": False,
            "message": f"Không tìm thấy sản phẩm '{name}' trong hệ thống hoặc không đủ dữ liệu từ các sàn.",
            "search_term": name,
            "suggestions": suggestions[:10]
        }
    
    return {
        "found": True,
        "search_term": name,
        "result_count": len([p for sublist in raw_data for p in sublist]),
        "message": f"Tìm thấy {platforms_with_results}/8 sàn có sản phẩm cho '{name}'"
    }


@app.get("/api/search/fallback")
async def search_fallback(name: str = Query(...), limit: int = Query(10)):
    """
    RAG-style fallback search:
    - Tìm kiếm fuzzy/partial matching trên tên sản phẩm
    - Chỉ gợi ý sản phẩm có ở >=3 sàn
    - Sắp xếp theo độ tương đồng với query
    - Trả về gợi ý sản phẩm tương tự nhất
    """
    if not name or len(name.strip()) < 2:
        return {"suggestions": []}

    search_name = clean_product_name(name)
    search_tokens = set(search_name.lower().split())

    async def get_similar_products(collection_name, platform_name):
        col = db[collection_name]
        try:
            cursor = col.find({}).limit(100)
            items = await cursor.to_list(length=100)
            for item in items:
                item['_platform_source'] = platform_name
            return items
        except Exception:
            return []

    # Lấy sản phẩm từ tất cả sàn, kèm tên sàn để đếm platform đúng
    raw_data = await asyncio.gather(*(
        get_similar_products(c, p) for p, c in STORE_COLLECTIONS.items()
    ))
    all_products = [p for sublist in raw_data for p in sublist]

    # Nhóm sản phẩm theo tên đã chuẩn hóa và đếm số sàn
    product_platforms = {}
    for p in all_products:
        p_name = p.get('name', '')
        p_clean = clean_product_name(p_name)
        if not p_clean:
            continue
        name_key = p_clean.lower().strip()
        platform = p.get('_platform_source', '')
        if not platform:
            continue
        if name_key not in product_platforms:
            product_platforms[name_key] = {
                'name': p_name,
                'platforms': set(),
                'products': []
            }
        product_platforms[name_key]['platforms'].add(platform)
        product_platforms[name_key]['products'].append(p)

    # Tính điểm similarity cho từng sản phẩm, chỉ lấy sản phẩm có >=3 sàn
    scored_products = []
    for name_key, data in product_platforms.items():
        if len(data['platforms']) < 3:
            continue

        p_name = data['name']
        p_clean = name_key
        p_tokens = set(p_clean.split())

        intersection = len(search_tokens & p_tokens)
        union = len(search_tokens | p_tokens) if (search_tokens | p_tokens) else 1
        jaccard_score = intersection / union

        brand_bonus = 0
        if any(token in p_clean for token in search_tokens if len(token) > 3):
            brand_bonus = 0.3

        platform_count_bonus = min(0.2, len(data['platforms']) * 0.05)

        total_score = jaccard_score + brand_bonus + platform_count_bonus

        if total_score > 0.1:
            products = data['products']
            products.sort(key=lambda x: parse_price(x.get('price', '')) or float('inf'))
            best_product = products[0]

            scored_products.append({
                "platform": best_product.get('_platform_source', best_product.get('platform', '')),
                "name": p_name,
                "current_price": parse_price(best_product.get('price')),
                "image": best_product.get('image', '') or best_product.get('image_url', ''),
                "link": best_product.get('product_url', '#'),
                "platform_count": len(data['platforms']),
                "similarity": round(total_score, 3)
            })

    scored_products.sort(key=lambda x: x['similarity'], reverse=True)
    seen_names = set()
    unique_suggestions = []
    for p in scored_products:
        name_key = p['name'].lower().strip()
        if name_key not in seen_names:
            seen_names.add(name_key)
            unique_suggestions.append(p)
            if len(unique_suggestions) >= limit:
                break

    return {"suggestions": unique_suggestions}


@app.get("/api/suggest")
async def suggest_products(name: str = Query(...), limit: int = Query(8)):
    """
    Gợi ý sản phẩm theo query (autocomplete):
    Tìm kiếm tên sản phẩm khớp query trên 8 sàn, trả về danh sách gợi ý.
    """
    search_name = clean_product_name(name)
    if not search_name:
        return {"suggestions": []}

    async def get_suggestions(collection_name, platform):
        col = db[collection_name]
        try:
            cursor = col.find(
                {"name": {"$regex": search_name.replace(" ", ".*"), "$options": "i"}}
            ).limit(limit)
            items = await cursor.to_list(length=limit)
            return [{
                "name": item.get('name', ''),
                "platform": platform,
                "price": parse_price(item.get('price_number') or item.get('price', '')),
                "image": item.get('image_url', '') or item.get('image', ''),
                "link": item.get('product_url', '#') or item.get('url', '#')
            } for item in items]
        except Exception:
            return []

    results = await asyncio.gather(
        *(get_suggestions(c, p) for p, c in STORE_COLLECTIONS.items())
    )
    suggestions = [s for sublist in results for s in sublist]

    # Loại bỏ trùng (name, platform), giới hạn kết quả
    seen = set()
    unique = []
    for s in suggestions:
        key = (s['name'].lower(), s['platform'].lower())
        if key not in seen:
            seen.add(key)
            unique.append(s)
        if len(unique) >= limit:
            break

    return {"suggestions": unique}


def _ai_cache_key(*parts):
    return "|".join(str(p) for p in parts)

def get_cached_ai(key):
    entry = ai_cache.get(key)
    if entry and (_time.time() - entry['ts']) < AI_CACHE_TTL:
        return entry['data']
    return None

def set_cached_ai(key, data):
    ai_cache[key] = {'ts': _time.time(), 'data': data}


@app.get("/api/compare")
async def get_comparison(brand: str = "iphone", name: str = Query(...), fast: bool = Query(False)):
    """
    So sánh giá sản phẩm trên 8 sàn.
    
    Query params:
    - name: tên sản phẩm
    - fast: nếu true, trả về kết quả cơ bản ngay (không chạy AI/LSTM), phù hợp khi cần tốc độ
    """
    # Kiểm tra cache trước (trả về ngay lập tức nếu đã có)
    cache_key = f"{brand}:{name.strip().lower()}:fast={fast}"
    now = _time.time()
    cached = compare_cache.get(cache_key)
    if cached and (now - cached['ts']) < COMPARE_CACHE_TTL:
        return cached['data']

    # Chuẩn hóa tên tìm kiếm
    search_name = clean_product_name(name)
    base_search_name = extract_model_base(name)

    async def get_candidates(collection_name):
        col = db[collection_name]
        cursor = col.find({"name": {"$regex": search_name.replace(" ", ".*"), "$options": "i"}}).limit(20)
        return await cursor.to_list(length=20)

    raw_data = await asyncio.gather(*(get_candidates(c) for c in STORE_COLLECTIONS.values()))
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

    # Tính giá thị trường min/max từ tất cả sản phẩm khớp (cho S_Price)
    market_prices = [parse_price(p.get('price', '')) for p in all_candidates]
    market_prices = [p for p in market_prices if p > 0]
    min_market_price = min(market_prices) if market_prices else None
    max_market_price = max(market_prices) if market_prices else None

    # Sử dụng ngày hiện tại từ hệ thống để làm mốc đồng bộ cho cả 8 sàn
    today = datetime.now()
    # Tạo danh sách 7 ngày: [T-6, T-5, T-4, T-3, T-2, T-1, T]
    master_date_list = [(today - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(6, -1, -1)]
    # Nhãn hiển thị trên biểu đồ (ví dụ: 12/04, 13/04...)
    display_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in master_date_list]

    # Với mỗi sàn, chọn sản phẩm rẻ nhất khớp model base
    store_results = []
    
    async def process_platform(source, collection_name, candidates):
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
            return None
        
        platform_candidates.sort(key=lambda x: x[0], reverse=True)
        best_candidates = [p for _, p in platform_candidates]
        best_candidates.sort(key=lambda p: parse_price(p.get('price', '')))
        target_product = best_candidates[0]

        if not target_product:
            return None
            
        p = target_product
        current_price = parse_price(p.get('price', ''))

        # --- BƯỚC 2: LỊCH SỬ GIÁ THỰC (không che giấu ngày thiếu dữ liệu) ---
        fc_cfg = forecaster.load_config()
        chart_days = int(fc_cfg.get("default_chart_days", 7))
        series_all = forecaster.distinct_prices(p.get('price_history', []))
        if not series_all and current_price > 0:
            series_all = [current_price]
        series_window = forecaster.build_daily_series(p.get('price_history', []), days=chart_days)
        series_history = forecaster.build_daily_series(
            p.get('price_history', []), days=int(fc_cfg.get("chart_max_days", 30))
        )
        last_crawl = series_window.get("last_observed_date") or "N/A"

        forecast_price = current_price
        forecast_info = {
            "forecast": current_price,
            "method": "insufficient_history",
            "method_name": "Bản ghi nhanh (fast=true) chưa chạy dự báo AI",
            "reason": "Endpoint đang ở chế độ fast=true: chỉ trả dữ liệu giá cơ bản, không chạy LSTM/PhoBERT.",
            "insufficient_history": True,
            "is_lstm_used": False,
            "hybrid_mode": None,
            "hybrid_note": None,
            "band": None,
            "profile": forecaster.profile_series(series_all),
            "models_compared": [],
            "sample_size": 0,
            "eval_protocol": "rolling_origin_backtest",
        }
        sentiment_data = comment_analyzer.empty_sentiment()
        pqs = 50
        pqs_label = {"label": "🟠 Chất lượng trung bình", "color": "orange"}
        pqs_breakdown = {}
        price_stats = calculate_price_stats(p.get('price_history', []))
        price_trend = get_price_trend(current_price, forecast_price)
        buy_recommendation = get_buy_recommendation(pqs, price_stats, current_price, forecast_price)
        lstm_metrics = {}

        if not fast:
            # --- BƯỚC 4: DỰ BÁO GIÁ — Hybrid Forecast Engine (LSTM + baseline, chọn theo backtest) ---
            ai_key = _ai_cache_key(
                "forecast_v2", p.get('_id'), len(series_all),
                tuple(series_all[-LOOK_BACK:]) if len(series_all) >= LOOK_BACK else ()
            )
            cached_ai = get_cached_ai(ai_key)
            if cached_ai:
                forecast_info = cached_ai['forecast_info']
            else:
                forecast_info = forecaster.forecast_next(series_all, lstm_model, scaler, fc_cfg)
                set_cached_ai(ai_key, {'forecast_info': forecast_info})

            forecast_price = forecast_info.get("forecast") or current_price
            lstm_metrics = build_lstm_metrics_payload(forecast_info)

            # --- BƯỚC 5: PHÂN TÍCH CẢM XÚC — hybrid PhoBERT + rule-based ---
            sentiment_key = _ai_cache_key("sentiment_v2", p.get('_id'), len(p.get('comments', [])))
            cached_sentiment = get_cached_ai(sentiment_key)
            if cached_sentiment:
                sentiment_data = cached_sentiment
            else:
                sentiment_data = analyze_comments_ai(p.get('comments', []))
                set_cached_ai(sentiment_key, sentiment_data)

            pqs_breakdown = calculate_pqs(
                p, sentiment_data, current_price=current_price, forecast_price=forecast_price,
                min_market_price=min_market_price, max_market_price=max_market_price,
                return_breakdown=True
            )
            pqs = pqs_breakdown["total"]
            pqs_label = get_pqs_label(pqs)
            price_trend = get_price_trend(current_price, forecast_price)
            buy_recommendation = get_buy_recommendation(pqs, price_stats, current_price, forecast_price)

        # --- BƯỚC 6: BIỂU ĐỒ (7 ngày gần nhất + điểm dự báo, kèm cờ ngày thiếu dữ liệu) ---
        chart_labels = list(series_window.get("labels") or []) + ["Dự báo"]
        chart_data = list(series_window.get("prices") or []) + [
            forecast_price if forecast_price and forecast_price > 0 else None
        ]
        chart_observed = list(series_window.get("observed") or []) + [True]
        chart_filled = list(series_window.get("filled") or []) + [False]

        return {
            "platform": source,
            "name": p.get('name'),
            "current_price": current_price,
            "forecast": forecast_price,
            "insufficient_history": bool(forecast_info.get("insufficient_history")),
            "forecast_method": forecast_info.get("method"),
            "forecast_method_name": forecast_info.get("method_name"),
            "forecast_method_reason": forecast_info.get("reason"),
            "forecast_band": forecast_info.get("band"),
            "hybrid_mode": forecast_info.get("hybrid_mode"),
            "hybrid_note": forecast_info.get("hybrid_note"),
            "is_lstm_used": forecast_info.get("is_lstm_used"),
            "models_compared": forecast_info.get("models_compared", []),
            "forecast_profile": forecast_info.get("profile"),
            "forecast_sample_size": forecast_info.get("sample_size"),
            "last_crawl_date": last_crawl,
            "image": p.get('image', '') or p.get('image_url', ''),
            "sentiment": sentiment_data,
            "chart": {
                "labels": chart_labels,
                "data": chart_data,
                "observed": chart_observed,
                "filled": chart_filled,
                "today_index": len(chart_labels) - 2,
                "forecast_index": len(chart_labels) - 1
            },
            "chart_history": {
                "labels": series_history.get("labels"),
                "dates": series_history.get("dates"),
                "prices": series_history.get("prices"),
                "observed": series_history.get("observed"),
                "filled": series_history.get("filled")
            },
            "chart_days_default": chart_days,
            "link": p.get('product_url', '#'),
            "pqs": pqs,
            "pqs_label": pqs_label,
            "pqs_breakdown": pqs_breakdown,
            "price_stats": price_stats,
            "price_trend": price_trend,
            "buy_recommendation": buy_recommendation,
            "lstm_metrics": lstm_metrics
        }

    # Parallelize platform processing
    platform_tasks = []
    for i, (source, collection_name) in enumerate(STORE_COLLECTIONS.items()):
        candidates = raw_data[i]
        platform_tasks.append(process_platform(source, collection_name, candidates))
    
    platform_results = await asyncio.gather(*platform_tasks, return_exceptions=True)
    store_results = [r for r in platform_results if r is not None and not isinstance(r, Exception)]

    # Sắp xếp theo giá tăng dần và trả về 3 sàn rẻ nhất
    store_results.sort(key=lambda r: r["current_price"] or 0)
    result = {"results": store_results[:3]}

    # Lưu vào cache
    compare_cache[cache_key] = {'ts': now, 'data': result}
    return result


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
    """Đăng nhập bằng email + mật khẩu. Nếu tài khoản chưa có, tự động đăng ký mới."""
    if not auth.is_valid_email(email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ")
    
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự")
    
    user = await auth.get_user_by_email(db, email)
    if not user:
        user = await auth.create_user(db, email, password, full_name="")
        token = auth.create_access_token({"sub": str(user["_id"])})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": auth.user_to_public(user),
            "new_user": True
        }
    
    if not auth.verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    token = auth.create_access_token({"sub": str(user["_id"])})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": auth.user_to_public(user),
        "new_user": False
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
        forecast_price = (product.get("forecast") or 0) or current_price
        current_pqs = calculate_pqs(
            product, sentiment_data,
            current_price=current_price,
            forecast_price=forecast_price
        )
        price_stats = calculate_price_stats(product.get("price_history", []))
        price_trend = get_price_trend(current_price, forecast_price)

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

# ============================================================
# AI INSIGHTS — số liệu thực nghiệm (Chương 4) + cấu hình model
# ============================================================
RESULTS_DIR = os.path.join(BASE_DIR, "results")


def _load_result_json(filename):
    """Đọc 1 file kết quả thực nghiệm trong backend/results (None nếu chưa có)."""
    path = os.path.join(RESULTS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_yaml_config(filename):
    """Đọc file cấu hình trong backend/config (None nếu thiếu PyYAML hoặc lỗi)."""
    path = os.path.join(BASE_DIR, "config", filename)
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _load_pqs_rqs_summary():
    """Chỉ lấy phần tổng hợp của báo cáo PQS/RQS (file gốc ~1.1MB)."""
    data = _load_result_json("evaluation_report_pqs_rqs_real_db.json")
    if not isinstance(data, dict):
        return None
    return {
        "pqs_stats": data.get("pqs_stats"),
        "rqs_stats": data.get("rqs_stats"),
        "recommendation_distribution": data.get("recommendation_distribution"),
        "brand_distribution": data.get("brand_distribution"),
        "top10_pqs_high": data.get("top10_pqs_high"),
    }


@app.get("/api/ai/insights")
async def ai_insights():
    """Số liệu thực nghiệm + cấu hình model cho dashboard "AI Model Insights".

    Nguồn dữ liệu: backend/results/*.json (sinh bởi backend/scripts/experiment_runner.py
    và các script evaluate_*.py). Không đọc file PQS/RQS 1.1MB để giữ response nhẹ.
    """
    cache_key = "ai_insights_v1"
    cached = get_cached_ai(cache_key)
    if cached:
        return cached

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": {
            "lstm_loaded": lstm_model is not None,
            "lstm_scaler_loaded": scaler is not None,
            "phobert_loaded": model_sent is not None,
            "phobert": comment_analyzer.get_analyzer_meta(model_sent),
            "label_map_sources": LABEL_MAP_SOURCES,
            "sentiment_label_map": {str(k): v for k, v in (SENTIMENT_LABEL_MAP or {}).items()},
        },
        "forecast_config": forecaster.get_config_rationale(),
        "pqs_weights": _load_yaml_config("pqs_weights.yaml"),
        "experiments": {
            "lstm_temporal": _load_result_json("lstm_temporal_results.json"),
            "forecast_selection": _load_result_json("forecast_selection_results.json"),
            "phobert_hybrid": _load_result_json("phobert_hybrid_results.json"),
            "aspect_model": _load_result_json("aspect_model_results.json"),
            "entity_resolution": _load_result_json("entity_resolution_results.json"),
            "api_benchmark": _load_result_json("api_benchmark_results.json"),
            "api_load_test": _load_result_json("api_load_test_results.json"),
            "pqs_rqs": _load_pqs_rqs_summary(),
        },
        "notes": [
            "lstm_metrics trên từng sản phẩm được tính bằng rolling-origin backtest (chỉ dùng dữ liệu quá khứ).",
            "forecast_method/reason cho biết Hybrid Engine đã chọn phương pháp nào và vì sao.",
            "Số liệu ở mục experiments lấy từ backend/results/*.json — chạy backend/scripts/experiment_runner.py để làm mới.",
        ],
    }
    set_cached_ai(cache_key, payload)
    return payload


@app.post("/api/collect-request")
async def create_collect_request(payload: dict = Body(default={})):
    """Ghi nhận yêu cầu thu thập dữ liệu cho sản phẩm chưa có trong hệ thống.

    KHÔNG crawl trực tiếp trong request (tránh treo server lúc demo); scraper sẽ xử lý
    danh sách pending trong lần chạy kế tiếp.
    """
    name = str((payload or {}).get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Thiếu tên sản phẩm")

    doc = {
        "name": name,
        "platforms": (payload or {}).get("platforms", []),
        "source": (payload or {}).get("source", "web"),
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    try:
        col = db.collect_requests
        await col.update_one({"name": name, "status": "pending"}, {"$set": doc}, upsert=True)
        pending = await col.count_documents({"status": "pending"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không ghi được yêu cầu: {e}")

    return {
        "ok": True,
        "message": f"Đã ghi nhận yêu cầu thu thập '{name}'. Hệ thống sẽ crawl trong lần chạy scraper kế tiếp.",
        "pending_requests": pending,
    }
