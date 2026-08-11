# -*- coding: utf-8 -*-
"""
Export comments từ MongoDB Atlas của datn sang file jsonl train PhoBERT.

- Kết nối: mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/
- Database: price_tracker
- Đọc TẤT CẢ collections có field comments
- Gán weak label sentiment bằng từ khóa (positive/neutral/negative)
- Xuất: data/phobert_train_sentiment_datn.jsonl
"""
import json
import os
import re
import sys
from pymongo import MongoClient

# Đảm bảo console in được tiếng Việt/emoji
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"
COLLECTIONS = [
    "products", "tgdd", "fpt", "cellphones", "viettelstore",
    "hoangha", "didongviet", "clickbuy", "mobilecity"
]
OUTPUT = os.path.join("data", "phobert_train_sentiment_datn.jsonl")

# Từ khóa weak label sentiment
POSITIVE_WORDS = [
    "tốt", "đẹp", "mượt", "nhanh", "xịn", "ưng", "hài lòng", "thích", "ok",
    "ổn", "tuyệt", "xuất sắc", "đáng mua", "rẻ", "giá tốt", "pin trâu",
    "chụp đẹp", "cấu hình mạnh", "màn hình đẹp", "đáng tiền", "bền", "nhẹ",
    "mỏng", "sang", "cao cấp", "đỉnh", "ngon", "chuẩn", "hợp lý", "ưng ý",
    "tuyệt vời", "hoàn hảo", "đáng giá", "mua được", "khuyên dùng", "recommend"
]
NEGATIVE_WORDS = [
    "tệ", "dở", "kém", "chậm", "lag", "đơ", "nóng", "tỏi", "hư", "lỗi",
    "thất vọng", "không nên mua", "phí tiền", "tạm", "chán", "tệ hại",
    "đen", "mờ", "nhòe", "rung", "ồn", "nặng", "dày", "xấu", "cùi",
    "dỏm", "giả", "trục trặc", "sự cố", "lỗi vặt", "khó chịu", "bực",
    "không đáng", "đắt", "chát", "quá đắt", "kém chất lượng"
]
NEUTRAL_WORDS = [
    "bình thường", "tạm được", "cũng được", "không sao", "chấp nhận được",
    "hỏi", "giá bao nhiêu", "còn hàng", "khuyến mãi", "giảm giá", "bảo hành",
    "ship", "giao hàng", "trả góp", "màu", "dung lượng", "so sánh"
]


def clean_text(text):
    """Làm sạch comment: bỏ khoảng trắng thừa, ký tự đặc biệt."""
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:500]  # Giới hạn độ dài


def weak_label(text):
    """Gán nhãn sentiment bằng từ khóa."""
    text_lower = text.lower()
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    neu_count = sum(1 for w in NEUTRAL_WORDS if w in text_lower)

    if pos_count > neg_count and pos_count > neu_count:
        return "positive"
    if neg_count > pos_count and neg_count > neu_count:
        return "negative"
    if neu_count > 0 and neu_count >= pos_count and neu_count >= neg_count:
        return "neutral"
    # Mặc định neutral nếu không có từ khóa rõ ràng
    return "neutral"


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]

    os.makedirs("data", exist_ok=True)
    seen = set()
    records = []

    print("🔍 Đang quét comments từ MongoDB Atlas (price_tracker)...")
    for col_name in COLLECTIONS:
        try:
            col = db[col_name]
            items = list(col.find({}, {"comments": 1}))
            count = 0
            for item in items:
                comments = item.get("comments", [])
                if not isinstance(comments, list):
                    continue
                for c in comments:
                    text = clean_text(c)
                    if not text or len(text) < 5:
                        continue
                    # Bỏ trùng lặp
                    if text in seen:
                        continue
                    seen.add(text)
                    records.append({
                        "text": text,
                        "label": weak_label(text)
                    })
                    count += 1
            print(f"  ✅ {col_name}: {count} comments")
        except Exception as e:
            print(f"  ⚠️ {col_name}: lỗi - {e}")

    # Ghi file
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Thống kê
    from collections import Counter
    label_counts = Counter(r["label"] for r in records)
    print(f"\n✅ Đã xuất {len(records)} comments -> {OUTPUT}")
    print(f"📊 Phân bố label: {dict(label_counts)}")


if __name__ == "__main__":
    main()