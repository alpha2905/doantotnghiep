import pickle
import joblib
import os

brands = ["iphone", "samsung", "oppo", "xiaomi"]

for brand in brands:
    old_path = f"backend/models/{brand}_scaler.pkl"
    new_path = f"backend/models/{brand}_scaler_fixed.joblib"
    
    if os.path.exists(old_path):
        try:
            # Cố gắng nạp bằng pickle
            with open(old_path, 'rb') as f:
                scaler = pickle.load(f)
            
            # Lưu lại bằng joblib (ổn định hơn cho mô hình AI)
            joblib.dump(scaler, new_path)
            print(f"✅ Đã fix xong scaler cho: {brand}")
        except Exception as e:
            print(f"❌ Không thể đọc file {brand}: {e}")