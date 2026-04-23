import numpy as np
import pandas as pd
import os
import joblib
import warnings
from datetime import datetime
from pymongo import MongoClient
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import ModelCheckpoint

warnings.filterwarnings('ignore')

# --- CẤU HÌNH ---
MONGO_URI = "mongodb://localhost:27017/"
MODEL_DIR = "models"
LOOK_BACK = 5 
BRANDS = ["iphone", "samsung", "oppo", "xiaomi"]

if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

client = MongoClient(MONGO_URI)

def load_and_clean_data():
    """Gom dữ liệu và lọc bỏ sản phẩm lỗi"""
    all_data = []
    databases = {
        "dmx_database": ["iphone_products", "samsung_products", "xiaomi_products", "oppo_products"],
        "fpt_database": ["iphone_full_data", "samsung_full_data", "xiaomi_full_data", "oppo_full_data"],
        "tgdd_database": ["iphone_master_data", "samsung_master_data", "xiaomi_master_data", "oppo_master_data"]
    }
    
    print("🔍 Đang quét Database...")
    for db_name, collections in databases.items():
        db = client[db_name]
        for col_name in collections:
            items = list(db[col_name].find({}, {"name": 1, "brand": 1, "price_history": 1}))
            for item in items:
                history = item.get("price_history", [])
                if isinstance(history, list) and len(history) > 0:
                    unique_history = {h['date']: float(h['price']) for h in history if h.get('price')}
                    if unique_history:
                        sorted_dates = sorted(unique_history.keys())
                        clean_prices = [unique_history[d] for d in sorted_dates]
                        all_data.append({
                            "name": item.get("name", "Unknown"),
                            "brand": str(item.get("brand", "iphone")).lower(),
                            "prices": clean_prices
                        })
    print(f"✅ Đã tải {len(all_data)} sản phẩm hợp lệ.")
    return all_data

def get_safe_sequence(prices, look_back=5):
    """Bù dữ liệu (Padding) nếu sản phẩm quá mới"""
    if len(prices) >= look_back:
        return np.array(prices[-look_back:])
    padding_size = look_back - len(prices)
    return np.array([prices[0]] * padding_size + prices)

def build_lstm_model():
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(LOOK_BACK, 1)),
        Dropout(0.2), # Tăng nhẹ dropout để chống overfit
        LSTM(32),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def train_brand_model(brand_name, all_data):
    print(f"\n🚀 Đang xử lý Brand: {brand_name.upper()}")
    
    # 1. Gom tất cả X và y từ từng sản phẩm riêng biệt (Tránh Data Leakage)
    all_X_samples = []
    all_y_samples = []
    
    scaler = MinMaxScaler()
    
    # Gom toàn bộ giá của brand để fit scaler (đảm bảo thang đo thống nhất)
    all_brand_prices = []
    for item in all_data:
        if brand_name in item['brand'] or brand_name in item['name'].lower():
            all_brand_prices.extend(item['prices'])
            
    if len(all_brand_prices) < 20:
        print(f"⚠️ {brand_name} quá ít dữ liệu, bỏ qua.")
        return

    # Fit scaler trên toàn bộ vùng giá của Brand
    prices_reshaped = np.array(all_brand_prices).reshape(-1, 1)
    scaler.fit(prices_reshaped)

    # 2. Tạo tập Train cho từng sản phẩm
    for item in all_data:
        if brand_name in item['brand'] or brand_name in item['name'].lower():
            # Scale giá của từng sản phẩm
            prod_prices = np.array(item['prices']).reshape(-1, 1)
            scaled_prod = scaler.transform(prod_prices).flatten()
            
            # Chỉ tạo mẫu nếu sản phẩm có đủ dữ liệu (hoặc dùng padding nếu cần)
            # Ở đây mình ưu tiên sản phẩm có ít nhất (LOOK_BACK + 1) ngày
            if len(scaled_prod) > LOOK_BACK:
                for i in range(len(scaled_prod) - LOOK_BACK):
                    all_X_samples.append(scaled_prod[i:i+LOOK_BACK])
                    all_y_samples.append(scaled_prod[i+LOOK_BACK])

    X = np.array(all_X_samples)
    y = np.array(all_y_samples)
    
    if len(X) == 0:
        print(f"⚠️ Không tạo được mẫu train cho {brand_name}.")
        return

    X = X.reshape(X.shape[0], X.shape[1], 1)

    # 3. Huấn luyện
    model_path = os.path.join(MODEL_DIR, f"{brand_name}_lstm_best.keras")
    if os.path.exists(model_path):
        print(f"🔄 Cập nhật kiến thức cho {brand_name}...")
        model = load_model(model_path)
        epochs = 20
    else:
        print(f"🆕 Khởi tạo Model mới cho {brand_name}...")
        model = build_lstm_model()
        epochs = 60

    model.fit(X, y, epochs=epochs, batch_size=32, verbose=1)
    model.save(model_path)
    joblib.dump(scaler, os.path.join(MODEL_DIR, f"{brand_name}_scaler.pkl"))
    print(f"✅ Đã lưu Model và Scaler cho {brand_name}")

def predict_next_7_days(brand_name, all_data):
    """Dự báo dựa trên chuỗi giá cuối cùng của Brand"""
    model_path = os.path.join(MODEL_DIR, f"{brand_name}_lstm_best.keras")
    scaler_path = os.path.join(MODEL_DIR, f"{brand_name}_scaler.pkl")
    
    if not os.path.exists(model_path): return None

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)
    
    # Lấy giá của sản phẩm có lịch sử mới nhất của hãng này
    latest_prices = []
    for item in reversed(all_data): # Ưu tiên các sp mới cập nhật
        if brand_name in item['brand'] or brand_name in item['name'].lower():
            latest_prices = item['prices']
            break
            
    if not latest_prices: return None

    input_seq = get_safe_sequence(latest_prices, LOOK_BACK)
    predictions = []
    curr_input = input_seq.tolist()

    for _ in range(7):
        # Scale input
        scaled_input = scaler.transform(np.array(curr_input[-LOOK_BACK:]).reshape(-1, 1))
        scaled_input = scaled_input.reshape(1, LOOK_BACK, 1)
        
        # Predict
        pred_scaled = model.predict(scaled_input, verbose=0)
        pred_price = scaler.inverse_transform(pred_scaled)[0][0]
        
        predictions.append(int(pred_price))
        curr_input.append(pred_price)
        
    return predictions

if __name__ == "__main__":
    print(f"🚀 BẮT ĐẦU CHƯƠNG TRÌNH AI - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    data = load_and_clean_data()
    
    for b in BRANDS:
        train_brand_model(b, data)
        
        forecast = predict_next_7_days(b, data)
        if forecast:
            print(f"🔮 DỰ BÁO {b.upper()} 7 NGÀY TỚI:")
            print(" -> ".join([f"{p:,.0f}đ" for p in forecast]))
    
    print("\n✨ HOÀN TẤT CẬP NHẬT TOÀN BỘ HỆ THỐNG AI.")