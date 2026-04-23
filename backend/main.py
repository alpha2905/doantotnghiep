import os
import numpy as np
import torch
import tensorflow as tf
import joblib
import asyncio
import random
import re
from datetime import datetime, timedelta
from collections import Counter
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from transformers import AutoTokenizer, RobertaForSequenceClassification
from contextlib import asynccontextmanager
import schema

# --- CẤU HÌNH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANDS = ["iphone", "samsung", "oppo", "xiaomi"]
LOOK_BACK = 5
ASPECT_LABELS = [
    "khác", "pin", "giá", "hiệu_năng", "màn_hình", "camera", 
    "thiết_kế", "loa_âm_thanh", "bảo_mật", "hệ_điều_hành", "phụ_kiện", "phục_vụ"
]

lstm_models, scalers = {}, {}
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, model_sent, model_aspect
    print("🚀 Hệ thống so sánh giá An Nguyễn đang khởi động...")
    
    # Load LSTM Models cho dự báo giá
    for brand in BRANDS:
        m_path = os.path.join(BASE_DIR, "models", f"{brand}_lstm_best.keras")
        s_path = os.path.join(BASE_DIR, "models", f"{brand}_scaler.pkl")
        if os.path.exists(m_path): 
            lstm_models[brand] = tf.keras.models.load_model(m_path)
        if os.path.exists(s_path): 
            scalers[brand] = joblib.load(s_path)
    
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
            local_files_only=True
        )
        
        print(f"📂 Loading aspect model from: {asp_path}")
        model_aspect = RobertaForSequenceClassification.from_pretrained(
            asp_path, 
            num_labels=12, 
            ignore_mismatched_sizes=True,
            local_files_only=True
        )
        
        model_sent.eval()
        model_aspect.eval()
        print("✅ AI Models Ready!")
    except Exception as e: 
        print(f"❌ AI Error: {e}")
        import traceback
        traceback.print_exc()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Kết nối MongoDB
client = AsyncIOMotorClient("mongodb://localhost:27017")
dbs = {
    "fpt": client.fpt_database, 
    "tgdd": client.tgdd_database, 
    "dmx": client.dmx_database
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
        ("giao diện", "hệ_điều_hành"),
        
        # PHỤ KIỆN
        ("sạc không dây", "phụ_kiện"), ("củ sạc", "phụ_kiện"),
        ("tai nghe", "phụ_kiện"), ("ốp lưng", "phụ_kiện"),
        ("cường lực", "phụ_kiện"), ("cáp sạc", "phụ_kiện"),
        ("phụ kiện", "phụ_kiện"), ("bảo hành", "phụ_kiện"),
        ("sạc", "phụ_kiện"), ("cáp", "phụ_kiện"),
        
        # PHỤC VỤ
        ("nhân viên tư vấn", "phục_vụ"), ("nhân viên", "phục_vụ"),
        ("phục vụ", "phục_vụ"), ("tư vấn", "phục_vụ"), 
        ("nhiệt tình", "phục_vụ"), ("chu đáo", "phục_vụ"),
        ("thái độ", "phục_vụ"), ("giao hàng", "phục_vụ"),
        ("shipper", "phục_vụ"), ("đóng gói", "phục_vụ")
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

@app.get("/api/compare")
async def get_comparison(brand: str = "iphone", name: str = Query(...)):
    # Chuẩn hóa tên tìm kiếm
    search_name = clean_product_name(name)
    base_search_name = extract_model_base(name)

    async def get_candidates(plat, db):
        col = f"{brand}_full_data" if plat == "fpt" else (f"{brand}_master_data" if plat == "tgdd" else f"{brand}_products")
        # Tìm kiếm mở rộng hơn một chút để lọc sau
        cursor = db[col].find({"name": {"$regex": search_name.replace(" ", ".*"), "$options": "i"}}).limit(20)
        return await cursor.to_list(length=20)

    raw_data = await asyncio.gather(*(get_candidates(p, dbs[p]) for p in dbs))
    for i, plat in enumerate(dbs.keys()):
        print(f"DEBUG: Platform {plat} found {len(raw_data[i])} items")

    # Logic Matching mới:
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
    best_model_base = scored_candidates[0][1]

    final_results = []
    plat_names = ["FPT", "TGDD", "DMX"]

    # Sử dụng ngày hiện tại từ hệ thống để làm mốc đồng bộ cho cả 3 sàn
    today = datetime.now()
    # Tạo danh sách 7 ngày: [T-6, T-5, T-4, T-3, T-2, T-1, T]
    master_date_list = [(today - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(6, -1, -1)]
    # Nhãn hiển thị trên biểu đồ (ví dụ: 12/04, 13/04...)
    display_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in master_date_list]

    for i, candidates in enumerate(raw_data):
        platform_candidates = []
        for p in candidates:
            p_name_clean = clean_product_name(p.get('name', ''))
            p_base = extract_model_base(p_name_clean)
            
            if best_model_base in p_base or p_base in best_model_base:
                sub_score = 0
                if p_base == best_model_base: sub_score += 10
                if search_name in p_name_clean: sub_score += 5
                platform_candidates.append((sub_score, p))
        
        scored_candidates = []
        for p in all_candidates:
            p_name_clean = clean_product_name(p.get('name', ''))
            p_base = extract_model_base(p_name_clean)
            
            score = 0
            # Tìm vị trí chính xác của model base (vd: "12") trong tên sản phẩm
            # Sử dụng Regex với boundary (\b) để tránh khớp nhầm "12" trong "128"
            match_exact = re.search(rf'\b{base_search_name}\b', p_name_clean)
            
            if match_exact:
                # 1. Thưởng cực lớn nếu tìm thấy model chính xác (vd: chữ "12" đứng riêng)
                score += 200
                
                # 2. Ưu tiên từ trái qua phải: vị trí càng gần đầu tên sản phẩm điểm càng cao
                pos = match_exact.start()
                score += max(0, 100 - pos)
                
                # 3. Nếu khớp hoàn toàn model base sau khi đã lọc sạch rác
                if p_base == base_search_name:
                    score += 50
            
            scored_candidates.append((score, p_base, p))

        # Sắp xếp theo điểm giảm dần và lấy model base tốt nhất
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_model_base = scored_candidates[0][1] if scored_candidates else base_search_name
        
        platform_candidates.sort(key=lambda x: x[0], reverse=True)
        target_product = platform_candidates[0][1] if platform_candidates else None

        if target_product:
            p = target_product
            
            # --- BƯỚC 2: LOGIC BÙ GIÁ (FORWARD FILL) ---
            # Chuyển lịch sử từ DB thành dict để lookup: { "2026-04-18": 12490000 }
            history_dict = {h['date']: float(h['price']) for h in p.get('price_history', []) if h.get('date')}
            
            final_prices = []
            # Lấy giá hiện tại làm giá mặc định khởi đầu nếu ngày đầu tiên trong chuỗi bị thiếu
            last_known_price = float(p.get('price_number') or 0)
            
            # Sắp xếp lịch sử để tìm giá thực tế cũ nhất có thể
            sorted_history_dates = sorted(history_dict.keys())
            if sorted_history_dates:
                last_known_price = history_dict[sorted_history_dates[0]]

            # Duyệt qua khung ngày chuẩn, nếu thiếu ngày nào thì lấy giá ngày trước đó
            for d_str in master_date_list:
                if d_str in history_dict:
                    last_known_price = history_dict[d_str]
                final_prices.append(last_known_price)

            # --- BƯỚC 3: DỰ BÁO GIÁ BẰNG LSTM ---
            forecast = 0
            if brand in lstm_models and final_prices:
                try:
                    # Sử dụng chuỗi giá đã được làm sạch và bù đắp để dự báo
                    # Đảm bảo đủ độ dài LOOK_BACK bằng cách padding nếu cần
                    input_prices = final_prices
                    if len(input_prices) < LOOK_BACK:
                        input_prices = [input_prices[0]] * (LOOK_BACK - len(input_prices)) + input_prices
                    
                    X_input = np.array(input_prices[-LOOK_BACK:]).reshape(-1, 1)
                    X_scaled = scalers[brand].transform(X_input)
                    pred = lstm_models[brand].predict(X_scaled.reshape(1, LOOK_BACK, 1), verbose=0)
                    forecast = int(scalers[brand].inverse_transform(pred)[0][0])
                except Exception as e:
                    print(f"Lỗi dự báo {plat_names[i]}: {e}")

            # --- BƯỚC 4: ĐÓNG GÓI KẾT QUẢ ---
            final_results.append({
                "platform": plat_names[i],
                "name": p.get('name'),
                "current_price": int(p.get('price_number') or 0),
                "forecast": forecast or int(p.get('price_number')),
                "last_crawl_date": sorted_history_dates[-1] if sorted_history_dates else "N/A",
                "image": p.get('image', ''),
                "sentiment": analyze_comments_ai(p.get('comments', [])),
                "chart": {
                    "labels": display_labels, # Luôn dùng chung 1 trục ngày
                    "data": final_prices      # Luôn trả về đủ 7 điểm dữ liệu
                },
                "link": p.get('url', '#')
            })

    return {"results": final_results}


@app.post("/api/ingest")
async def api_ingest(platform: str = Query(...), brand: str = Query(...), payload: dict = None):
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing product payload")
    if platform not in dbs:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")
    try:
        normalized = schema.normalize_product(payload, brand=brand, platform=platform)
        col_name = f"{brand}_full_data" if platform == "fpt" else (f"{brand}_master_data" if platform == "tgdd" else f"{brand}_products")
        await schema.upsert_product(dbs[platform], col_name, normalized)
        return {"ok": True, "stored": True, "name": normalized.get("name")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
# uvicorn main:app --reload