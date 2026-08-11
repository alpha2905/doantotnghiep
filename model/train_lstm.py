# -*- coding: utf-8 -*-
"""
Train LSTM tổng quát (1 model duy nhất) đọc trực tiếp MongoDB Atlas của datn.

- Kết nối: mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/
- Database: price_tracker
- Đọc TẤT CẢ 9 collections: products, tgdd, fpt, cellphones, viettelstore,
  hoangha, didongviet, clickbuy, mobilecity
- Không giới hạn brand → user query tùy ý ở FE
- Lọc sản phẩm có price_history >= 6 điểm (tối thiểu để tạo mẫu với LOOK_BACK=5)
- Xuất model: backend/models/general_lstm_best.keras + general_scaler.pkl
"""
import numpy as np
import os
import re
import sys
import joblib
import warnings
from datetime import datetime
from pymongo import MongoClient
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import ModelCheckpoint

warnings.filterwarnings('ignore')

# Đảm bảo console in được tiếng Việt/emoji
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_price_value(h):
    """Lấy giá trị số từ price_history entry.

    Hỗ trợ 2 dạng:
    - price_value: số (int/float) — collection products
    - price: string VND ("52.990.000 đ", "22,890,000 ₫", "12.750.000đ")
    """
    pv = h.get("price_value")
    if pv is not None:
        try:
            pv = float(pv)
            if pv > 0:
                return pv
        except (TypeError, ValueError):
            pass

    price_str = h.get("price")
    if price_str is not None:
        digits = re.sub(r"[^\d]", "", str(price_str))
        if digits:
            try:
                pv = float(digits)
                if pv > 0:
                    return pv
            except (TypeError, ValueError):
                pass
    return None

# --- CẤU HÌNH ---
MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"
COLLECTIONS = [
    "products", "tgdd", "fpt", "cellphones", "viettelstore",
    "hoangha", "didongviet", "clickbuy", "mobilecity"
]
MODEL_DIR = os.path.join("backend", "models")
LOOK_BACK = 5
MIN_HISTORY = 6  # Số điểm price_history tối thiểu để train

if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)


def load_and_clean_data():
    """Gom dữ liệu từ TẤT CẢ collections của datn, lọc sản phẩm đủ lịch sử giá."""
    all_data = []
    db = client[MONGO_DB]

    print("🔍 Đang quét MongoDB Atlas (price_tracker)...")
    for col_name in COLLECTIONS:
        try:
            col = db[col_name]
            items = list(col.find({}, {"name": 1, "source": 1, "price_history": 1}))
            valid = 0
            for item in items:
                history = item.get("price_history", [])
                if not isinstance(history, list) or len(history) < MIN_HISTORY:
                    continue

                # Gom giá theo ngày (scraped_at -> date, price -> giá trị số)
                unique_history = {}
                for h in history:
                    if not h:
                        continue
                    price_val = parse_price_value(h)
                    if price_val is None:
                        continue

                    scraped_at = h.get("scraped_at")
                    if isinstance(scraped_at, datetime):
                        date_str = scraped_at.strftime("%Y-%m-%d")
                    else:
                        date_str = str(scraped_at)[:10]

                    # Nếu cùng ngày, giữ giá cuối cùng trong ngày
                    unique_history[date_str] = price_val

                if len(unique_history) < MIN_HISTORY:
                    continue

                sorted_dates = sorted(unique_history.keys())
                clean_prices = [unique_history[d] for d in sorted_dates]
                all_data.append({
                    "name": item.get("name", "Unknown"),
                    "source": str(item.get("source", "")),
                    "prices": clean_prices
                })
                valid += 1
            print(f"  ✅ {col_name}: {valid} sản phẩm hợp lệ (≥{MIN_HISTORY} điểm giá)")
        except Exception as e:
            print(f"  ⚠️ {col_name}: lỗi - {e}")

    print(f"✅ Đã tải tổng cộng {len(all_data)} sản phẩm hợp lệ.")
    return all_data


def build_lstm_model():
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(LOOK_BACK, 1)),
        Dropout(0.2),
        LSTM(32),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model


def train_general_model(all_data):
    """Train 1 model LSTM tổng quát trên tất cả sản phẩm (không phân biệt brand)."""
    print("\n🚀 Đang train Model LSTM TỔNG QUÁT (tất cả sản phẩm)...")

    # 1. Gom toàn bộ giá để fit scaler (thang đo thống nhất)
    all_prices = []
    for item in all_data:
        all_prices.extend(item['prices'])

    if len(all_prices) < 20:
        print("⚠️ Quá ít dữ liệu, bỏ qua.")
        return

    scaler = MinMaxScaler()
    prices_reshaped = np.array(all_prices).reshape(-1, 1)
    scaler.fit(prices_reshaped)

    # 2. Tạo tập train từ từng sản phẩm riêng biệt (tránh Data Leakage)
    all_X_samples = []
    all_y_samples = []

    for item in all_data:
        prod_prices = np.array(item['prices']).reshape(-1, 1)
        scaled_prod = scaler.transform(prod_prices).flatten()

        # Chỉ tạo mẫu nếu sản phẩm có đủ dữ liệu (> LOOK_BACK)
        if len(scaled_prod) > LOOK_BACK:
            for i in range(len(scaled_prod) - LOOK_BACK):
                all_X_samples.append(scaled_prod[i:i + LOOK_BACK])
                all_y_samples.append(scaled_prod[i + LOOK_BACK])

    X = np.array(all_X_samples)
    y = np.array(all_y_samples)

    if len(X) == 0:
        print("⚠️ Không tạo được mẫu train nào.")
        return

    X = X.reshape(X.shape[0], X.shape[1], 1)
    print(f"📊 Tổng số mẫu train: {len(X)}")

    # 3. Huấn luyện
    model_path = os.path.join(MODEL_DIR, "general_lstm_best.keras")
    scaler_path = os.path.join(MODEL_DIR, "general_scaler.pkl")

    if os.path.exists(model_path):
        print("🔄 Cập nhật kiến thức cho Model tổng quát...")
        model = load_model(model_path)
        epochs = 20
    else:
        print("🆕 Khởi tạo Model tổng quát mới...")
        model = build_lstm_model()
        epochs = 60

    checkpoint = ModelCheckpoint(
        model_path, monitor='loss', save_best_only=True, verbose=1
    )
    model.fit(X, y, epochs=epochs, batch_size=32, verbose=1, callbacks=[checkpoint])
    model.save(model_path)
    joblib.dump(scaler, scaler_path)
    print(f"✅ Đã lưu Model và Scaler: {model_path}")


if __name__ == "__main__":
    print(f"🚀 BẮT ĐẦU CHƯƠNG TRÌNH AI - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    data = load_and_clean_data()
    train_general_model(data)
    print("\n✨ HOÀN TẤT CẬP NHẬT HỆ THỐNG AI.")