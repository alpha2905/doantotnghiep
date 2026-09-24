# -*- coding: utf-8 -*-
"""
Script Đánh giá & So sánh Thực nghiệm Dự báo Giá (REAL LSTM checkpoint):
- Chia dữ liệu theo thời gian (Temporal Split: 80% Train, 20% Test CHỈ dùng đánh giá)
- Nạp checkpoint THỰC TẾ: backend/models/general_lstm_best.pth + general_scaler.pkl
- Phân tích nhân quả (Causal Backtest off-by-one): Mỗi dự báo chỉ sử dụng cửa sổ quá khứ look_back
- So sánh: PyTorch LSTM (Look-back=5, mô hình thực tế) vs Baseline Naive & Moving Average (3)
- Đánh giá chỉ số: MAE, RMSE, MAPE, Directional Accuracy
"""
import os
import sys
import re
import joblib
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

import torch
import torch.nn as nn

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

_orig_tl = torch.load
def _p(*a, **k):
    k['weights_only'] = False
    return _orig_tl(*a, **k)
torch.load = _p

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"
COLLECTIONS = ["products", "tgdd", "fpt", "cellphones", "hoangha", "didongviet", "clickbuy", "mobilecity"]

# Đường dẫn tới checkpoint THỰC TẾ LSTM (backend/models)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
LSTM_PTH = os.path.join(BASE_DIR, "models", "general_lstm_best.pth")
LSTM_SCALER = os.path.join(BASE_DIR, "models", "general_scaler.pkl")
LOOK_BACK_TRAINED = 5   # Mô hình được huấn luyện với LOOK_BACK=5
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


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
            xt = torch.tensor(x, dtype=torch.float32)
            return self.forward(xt).cpu().numpy()


def load_real_model():
    """Nạp checkpoint LSTM đã huấn luyện + bộ chuẩn hóa Scaler. Trả về (model, scaler) hoặc (None, None)."""
    if not (os.path.exists(LSTM_PTH) and os.path.exists(LSTM_SCALER)):
        return None, None
    model = PyTorchLSTM()
    model.load_state_dict(torch.load(LSTM_PTH, map_location='cpu'))
    model.eval()
    scaler = joblib.load(LSTM_SCALER)
    return model, scaler


def backtest_lstm(prices, model, scaler, look_back):
    """Backtest nhân quả: Với mỗi i, đưa ra dự báo từ cửa sổ prices[i-look_back:i] -> prices[i]."""
    actual, predicted = [], []
    if model is None or scaler is None:
        return None, None
    for i in range(look_back, len(prices)):
        window = prices[i - look_back:i]
        w = np.array(window).reshape(-1, 1)
        try:
            w_scaled = scaler.transform(w).reshape(1, look_back, 1)
            pred_scaled = model.predict(w_scaled)
            pred_price = float(scaler.inverse_transform(pred_scaled)[0][0])
            if pred_price > 0:
                actual.append(prices[i])
                predicted.append(pred_price)
        except Exception:
            continue
    return actual, predicted


def parse_price_value(h):
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


def compute_metrics(actual, predicted):
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    mae = mean_absolute_error(actual, predicted)
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100 if len(actual) else 0.0
    correct = total = 0
    for i in range(1, len(actual)):
        ac = actual[i] - actual[i - 1]
        pc = predicted[i] - predicted[i - 1]
        if ac != 0:
            total += 1
            if (ac > 0 and pc > 0) or (ac < 0 and pc < 0) or \
               (abs(ac) < 0.01 * actual[i] and abs(pc) < 0.01 * actual[i]):
                correct += 1
    da = (correct / total * 100) if total else 0.0
    return mae, rmse, mape, da


def main():
    print("\n" + "=" * 82)
    print("THỰC NGHIỆM DỰ BÁO GIÁ CHUỖI THỜI GIAN (REAL LSTM CHECKPOINT)")
    print("=" * 82)

    # --- 1. Nạp checkpoint LSTM thực tế ---
    model, scaler = load_real_model()
    if model is None:
        print(f"❌ KHÔNG THẤY CHECKPOINT LSTM THỰC TẾ TẠI: {LSTM_PTH}")
        print("   (Vui lòng chạy lệnh: python backend/model/train_lstm.py trước)")
        return
    print(f"✅ Đã tải checkpoint LSTM THỰC TẾ: {LSTM_PTH}")

    # --- 2. Lấy dữ liệu chuỗi giá (MongoDB / Phương án dự phòng) ---
    best_series = []
    best_platform = ""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
        db = client[MONGO_DB]
        for col_name in COLLECTIONS:
            try:
                for doc in db[col_name].find({"price_history": {"$exists": True}}):
                    ph = doc.get("price_history", [])
                    prices = []
                    for entry in ph:
                        p = parse_price_value(entry)
                        if p:
                            prices.append(p)
                    if len(prices) > len(best_series):
                        best_series = prices
                        best_platform = col_name
            except Exception:
                pass
        client.close()
    except Exception as e:
        print(f"⚠️ Kết nối MongoDB không thành công ({e}). Sử dụng chuỗi dữ liệu giả lập dự phòng.")

    if len(best_series) < 30:
        np.random.seed(42)
        base = 32990000
        trend = np.linspace(0, -1500000, 60)
        noise = np.random.normal(0, 100000, 60)
        best_series = list(base + trend + noise)
        print("⚠️ Sử dụng chuỗi giá giả lập (Dữ liệu MongoDB trả về không đủ độ dài).")
    
    prices = best_series
    N = len(prices)
    split_idx = int(N * 0.8)
    print(f"\n📊 Dữ liệu: {N} mốc giá từ {best_platform or 'simulated'}")
    print(f"   Train (Temporal): {split_idx} | Test (Temporal): {N - split_idx}")

    # --- 3. Baselines trên cửa sổ Temporal Test ---
    test_actual = prices[split_idx:]
    test_naive = prices[split_idx - 1:N - 1]
    test_ma3 = [np.mean(prices[max(0, i - 3):i]) for i in range(split_idx, N)]
    test_ma7 = [np.mean(prices[max(0, i - 7):i]) for i in range(split_idx, N)]
    test_last = [prices[split_idx - 1]] * len(test_actual)

    baseline_preds = {
        "Naive (Giá hôm qua)": test_naive,
        "Moving Avg 3 ngày": test_ma3,
        "Moving Avg 7 ngày": test_ma7,
        "Last Value": test_last,
    }

    # --- 4. LSTM với nhiều LOOK_BACK khác nhau ---
    look_backs = [5, 7, 14, 30]
    lstm_results = {}
    
    for lb in look_backs:
        l_actual, l_pred = [], []
        for i in range(lb, N):
            if i < split_idx:
                continue
            window = prices[i - lb:i]
            w = np.array(window).reshape(-1, 1)
            try:
                ws = scaler.transform(w).reshape(1, lb, 1)
                ps = model.predict(ws)
                pp = float(scaler.inverse_transform(ps)[0][0])
                if pp > 0:
                    l_actual.append(prices[i])
                    l_pred.append(pp)
            except Exception:
                continue
        
        if l_actual:
            mae, rmse, mape, da = compute_metrics(l_actual, l_pred)
            lstm_results[lb] = {
                "mae": mae, "rmse": rmse, "mape": mape, "da": da,
                "samples": len(l_actual)
            }

    # --- 5. Bảng so sánh ---
    def row(name, mae, rmse, mape, da, samples=None):
        r = {"Mô hình / Phương pháp": name,
             "MAE (VNĐ)": f"{mae:,.0f}" if not np.isnan(mae) else "-",
             "RMSE (VNĐ)": f"{rmse:,.0f}" if not np.isnan(rmse) else "-",
             "MAPE (%)": f"{mape:.2f}%" if not np.isnan(mape) else "-",
             "Direction Acc (%)": f"{da:.1f}%" if not np.isnan(da) else "-"}
        if samples is not None:
            r["Samples"] = str(samples)
        return r

    results_table = []
    
    # Baselines
    for name, preds in baseline_preds.items():
        mae, rmse, mape, da = compute_metrics(test_actual, preds)
        results_table.append(row(name, mae, rmse, mape, da, len(test_actual)))
    
    # LSTM models
    for lb, metrics in lstm_results.items():
        results_table.append(row(
            f"LSTM (LOOK_BACK={lb})", 
            metrics["mae"], metrics["rmse"], metrics["mape"], metrics["da"],
            metrics["samples"]
        ))

    print("\n--- KẾT QUẢ ĐÁNH GIÁ (Temporal Split 80/20) ---")
    df = pd.DataFrame(results_table)
    print(df.to_string(index=False))
    
    # Lưu kết quả
    import json
    output_path = os.path.join(RESULTS_DIR, "lstm_temporal_results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "data_source": best_platform or "simulated",
            "total_points": N,
            "train_size": split_idx,
            "test_size": N - split_idx,
            "look_backs_tested": look_backs,
            "results": results_table
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Kết quả đã lưu: {output_path}")
    
    # Phân tích LOOK_BACK tốt nhất
    if lstm_results:
        best_lb = min(lstm_results.items(), key=lambda x: x[1]["mae"])
        print(f"\n🏆 LOOK_BACK tốt nhất: {best_lb[0]} ngày (MAE={best_lb[1]['mae']:,.0f} VNĐ)")


if __name__ == "__main__":
    main()