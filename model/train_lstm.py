# -*- coding: utf-8 -*-
"""
Train LSTM tổng quát (1 model duy nhất) đọc trực tiếp MongoDB Atlas của datn.

- Kết nối: mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/
- Database: price_tracker
- Đọc TẤT CẢ 9 collections: products, tgdd, fpt, cellphones, viettelstore,
  hoangha, didongviet, clickbuy, mobilecity
- Không giới hạn brand → user query tùy ý ở FE
- Lọc sản phẩm có price_history >= 6 điểm (tối thiểu để tạo mẫu với LOOK_BACK=5)
- Xuất model: backend/models/general_lstm_best.pth + general_scaler.pkl
"""
import os
import re
import sys
import joblib
import warnings
from datetime import datetime
import numpy as np
from pymongo import MongoClient
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

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

    X = np.array(all_X_samples, dtype=np.float32)
    y = np.array(all_y_samples, dtype=np.float32)

    if len(X) == 0:
        print("⚠️ Không tạo được mẫu train nào.")
        return

    X = X.reshape(X.shape[0], X.shape[1], 1)
    print(f"📊 Tổng số mẫu train: {len(X)}")

    # 3. Huấn luyện PyTorch Model
    model_path = os.path.join(MODEL_DIR, "general_lstm_best.pth")
    scaler_path = os.path.join(MODEL_DIR, "general_scaler.pkl")

    model = PyTorchLSTM()

    if os.path.exists(model_path):
        print("🔄 Cập nhật kiến thức cho Model tổng quát...")
        try:
            model.load_state_dict(torch.load(model_path, map_location='cpu'))
        except Exception as e:
            print(f"⚠️ Không thể load model cũ, tạo model mới: {e}")
        epochs = 20
    else:
        print("🆕 Khởi tạo Model tổng quát mới...")
        epochs = 60

    dataset = TensorDataset(torch.tensor(X), torch.tensor(y).unsqueeze(1))
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    best_loss = float('inf')
    model.train()

    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * batch_X.size(0)

        epoch_loss = running_loss / len(X)
        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch {epoch}/{epochs} - loss: {epoch_loss:.6f}")

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            torch.save(model.state_dict(), model_path)

    joblib.dump(scaler, scaler_path)
    print(f"✅ Đã lưu Model ({model_path}) và Scaler ({scaler_path}) (Best Loss: {best_loss:.6f})")


if __name__ == "__main__":
    print(f"🚀 BẮT ĐẦU CHƯƠNG TRÌNH AI - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    data = load_and_clean_data()
    train_general_model(data)
    print("\n✨ HOÀN TẤT CẬP NHẬT HỆ THỐNG AI.")
