# -*- coding: utf-8 -*-
"""Export comments từ MongoDB 8 sàn thành JSONL để train PhoBERT."""
import os, sys, json, random
from collections import Counter
from pymongo import MongoClient

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"
STORE_COLLECTIONS = ["fpt", "tgdd", "cellphones", "hoangha", "didongviet", "viettelstore", "clickbuy", "mobilecity"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Weak-label từ khóa
strong_neg = ["hỏng","lỗi","tệ","kém","thất vọng","lừa đảo","hư","trả hàng","vỡ ảnh","treo máy","tắt nguồn","crash","bug","mờ","nóng quá","chậm","đơ","lag"]
neg_words = ["đắt quá","kém chất lượng","tụt pin nhanh","chai pin","giật lag","rè","hết pin nhanh"]
pos_words = ["rất tốt","cực tốt","quá tốt","đáng mua","hài lòng","ưng ý","chất lượng","mượt","ổn định","pin trâu","sắc nét","sang trọng","rõ nét","ngon"]
question_words = ["không ạ","không nhỉ","có không","bao nhiêu","thế nào","khi nào","tư vấn","hỏi","còn không","còn hàng không","còn k ạ","shop còn","có hàng không"]

aspect_kw = [
    ("camera chụp","camera"),("camera sau","camera"),("camera trước","camera"),("chụp đêm","camera"),
    ("chụp ảnh","camera"),("chụp xóa phông","camera"),("góc siêu rộng","camera"),("góc rộng","camera"),
    ("chống rung","camera"),("vỡ ảnh","camera"),("quay phim","camera"),("quay video","camera"),
    ("ống kính","camera"),("selfie","camera"),("xóa phông","camera"),("hình ảnh","camera"),
    ("ảnh","camera"),("video","camera"),("camera","camera"),("chụp","camera"),("quay","camera"),
    ("nét","camera"),("mờ","camera"),("zoom","camera"),
    ("dung lượng pin","pin"),("thời lượng pin","pin"),("thời gian sử dụng pin","pin"),("tụt pin nhanh","pin"),
    ("tụt pin","pin"),("chai pin","pin"),("sạc không dây","pin"),("sạc nhanh","pin"),("sạc pin","pin"),
    ("pin yếu","pin"),("pin trâu","pin"),("hết pin","pin"),("cắm sạc","pin"),("dung lượng","pin"),
    ("mah","pin"),("pin","pin"),
    ("tần số quét","màn_hình"),("độ phân giải màn","màn_hình"),("màn hình","màn_hình"),("màn cong","màn_hình"),
    ("tai thỏ","màn_hình"),("đục lỗ","màn_hình"),("hiển thị","màn_hình"),("oled","màn_hình"),("amoled","màn_hình"),
    ("độ sáng","màn_hình"),("màu sắc","màn_hình"),("sắc nét","màn_hình"),("độ phân giải","màn_hình"),
    ("cảm ứng","màn_hình"),("màn","màn_hình"),
    ("giảm giá","giá"),("trả góp","giá"),("khuyến mãi","giá"),("giá cả","giá"),("đáng tiền","giá"),
    ("giá","giá"),("tiền","giá"),("rẻ","giá"),("đắt","giá"),("hợp lý","giá"),("sale","giá"),("bù","giá"),("trả trước","giá"),
    ("thiết kế","thiết_kế"),("ngoại hình","thiết_kế"),("chất liệu","thiết_kế"),("hoàn thiện","thiết_kế"),
    ("vỏ","thiết_kế"),("tróc","thiết_kế"),("cầm","thiết_kế"),("mỏng","thiết_kế"),("nhẹ","thiết_kế"),
    ("sang trọng","thiết_kế"),("sang","thiết_kế"),("đẹp","thiết_kế"),("màu sắc","thiết_kế"),("màu","thiết_kế"),
    ("hiệu năng","hiệu_năng"),("đa nhiệm","hiệu_năng"),("nóng máy","hiệu_năng"),("chơi game nặng","hiệu_năng"),
    ("chơi game","hiệu_năng"),("chiến game","hiệu_năng"),("mượt","hiệu_năng"),("lag","hiệu_năng"),("giật","hiệu_năng"),
    ("fps","hiệu_năng"),("chip","hiệu_năng"),("ram","hiệu_năng"),("tốc độ","hiệu_năng"),("nhanh","hiệu_năng"),
    ("chậm","hiệu_năng"),("đơ","hiệu_năng"),("xử lý","hiệu_năng"),("app","hiệu_năng"),("phần mềm","hiệu_năng"),("nóng","hiệu_năng"),
    ("âm bass","loa_âm_thanh"),("âm thanh","loa_âm_thanh"),("loa ngoài","loa_âm_thanh"),("loa trong","loa_âm_thanh"),
    ("nghe gọi","loa_âm_thanh"),("gọi điện","loa_âm_thanh"),("nghe nhạc","loa_âm_thanh"),("micro","loa_âm_thanh"),
    ("mic","loa_âm_thanh"),("rè","loa_âm_thanh"),("loa","loa_âm_thanh"),("volume","loa_âm_thanh"),("nghe","loa_âm_thanh"),
    ("nhận diện khuôn mặt","bảo_mật"),("mở khóa khuôn mặt","bảo_mật"),("face id","bảo_mật"),("faceid","bảo_mật"),
    ("vân tay","bảo_mật"),("mật khẩu","bảo_mật"),("khóa máy","bảo_mật"),("bảo mật","bảo_mật"),("mở khóa","bảo_mật"),
    ("hệ điều hành","hệ_điều_hành"),("bản cập nhật","hệ_điều_hành"),("cập nhật phần mềm","hệ_điều_hành"),
    ("giao diện người dùng","hệ_điều_hành"),("ios","hệ_điều_hành"),("android","hệ_điều_hành"),
    ("update","hệ_điều_hành"),("giao diện","hệ_điều_hành")
]
aspect_kw.sort(key=lambda x: len(x[0]), reverse=True)

def weak_sent(text):
    t = text.lower()
    if any(q in t for q in question_words): return "neutral"
    if any(n in t for n in strong_neg + neg_words): return "negative"
    if any(p in t for p in pos_words): return "positive"
    return "neutral"

def weak_aspect(text):
    t = text.lower()
    for kw, asp in aspect_kw:
        if kw in t: return asp
    return "khác"

def extract(comments):
    out = []
    if isinstance(comments, list):
        for c in comments:
            if isinstance(c, str) and c.strip(): out.append(c.strip())
            elif isinstance(c, dict):
                t = c.get("text") or c.get("content") or c.get("comment") or ""
                if isinstance(t, str) and t.strip(): out.append(t.strip())
    elif isinstance(comments, str) and comments.strip(): out.append(comments.strip())
    return out

def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    all_comments = []
    for col_name in STORE_COLLECTIONS:
        try:
            col = db[col_name]
            count = 0
            for doc in col.find({"comments": {"$exists": True}}, {"comments": 1}):
                for c in extract(doc.get("comments")):
                    all_comments.append(c); count += 1
            print(f"  ✅ {col_name}: {count} comments")
        except Exception as e:
            print(f"  ⚠️ {col_name}: {e}")
    print(f"✅ Tổng {len(all_comments)} comments")

    if not all_comments:
        print("❌ Không có comment. Dừng."); return

    # Sentiment
    sent_records = [{"text": c, "label": weak_sent(c)} for c in all_comments]
    counts = Counter(r["label"] for r in sent_records)
    print(f"📊 Sentiment trước cân bằng: {dict(counts)}")
    min_c = min(counts.values())
    balanced = []
    for lbl in counts:
        pool = [r for r in sent_records if r["label"] == lbl]
        random.shuffle(pool)
        balanced.extend(pool[:min_c])
    random.shuffle(balanced)
    print(f"📊 Sentiment sau cân bằng: {dict(Counter(r['label'] for r in balanced))}")
    sent_file = os.path.join(DATA_DIR, "phobert_train_sentiment_datn_balanced.jsonl")
    with open(sent_file, "w", encoding="utf-8") as f:
        for r in balanced: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✅ Lưu {len(balanced)} mẫu sentiment → {sent_file}")

    # Aspect
    asp_records = [{"text": c, "label": weak_aspect(c)} for c in all_comments]
    asp_counts = Counter(r["label"] for r in asp_records)
    print(f"📊 Aspect: {dict(asp_counts)}")
    valid = {l for l, cnt in asp_counts.items() if cnt >= 3}
    filtered = [r for r in asp_records if r["label"] in valid]
    print(f"📊 Số lớp aspect hợp lệ: {len(valid)}")
    asp_file = os.path.join(DATA_DIR, "phobert_train_aspect.jsonl")
    with open(asp_file, "w", encoding="utf-8") as f:
        for r in filtered: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✅ Lưu {len(filtered)} mẫu aspect → {asp_file}")

    client.close()
    print("✨ HOÀN TẤT EXPORT.")

if __name__ == "__main__":
    main()