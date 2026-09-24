# -*- coding: utf-8 -*-
"""
Script Đánh giá Thực nghiệm PQS / RQS / Recommendation Engine
trên DỮ LIỆU THỰC TẾ từ MongoDB
================================================================
Đọc sản phẩm thật từ 8 collection trong DB, tính:
  - Sentiment stats từ comments (rule-based, giống analyze_comments_ai)
  - PQS, RQS, get_pqs_label, get_price_trend, get_buy_recommendation
  - Thống kê theo platform, brand, phân phối PQS, phân phối recommendation

Lưu báo cáo JSON + in bảng tổng hợp ra console.
"""
import os
import sys
import json
import time
import re
from datetime import datetime
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# MongoDB config (giống main.py)
# ---------------------------------------------------------------------------
MONGO_URI = os.environ.get(
    "MONGO_URI",
    os.environ.get(
        "MONGODB_URI",
        "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
    )
)
MONGO_DB = os.environ.get("MONGO_DB", "price_tracker")
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
BRANDS = ["iphone", "samsung", "oppo", "xiaomi"]

# ---------------------------------------------------------------------------
# Import các hàm cần đánh giá từ main.py (không khởi động FastAPI)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Chặn FastAPI startup khi import main
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "price_tracker_eval")

from main import (
    calculate_pqs,
    get_pqs_label,
    calculate_price_stats,
    get_price_trend,
    get_buy_recommendation,
    calculate_rqs,
    parse_price,
)

# ---------------------------------------------------------------------------
# Tiện ích sentiment (rule-based, giống analyze_comments_ai nhưng đơn giản hơn)
# ---------------------------------------------------------------------------
strong_neg = ["hỏng", "lỗi", "tệ", "kém", "thất vọng", "lừa đảo", "hư", "trả hàng", "vỡ ảnh", "treo máy", "tắt nguồn", "crash", "bug", "mờ", "nóng quá", "chậm", "đơ", "lag"]
neg_words = ["đắt quá", "kém chất lượng", "tụt pin nhanh", "chai pin", "giật lag", "rè", "hết pin nhanh"]
pos_words = ["rất tốt", "cực tốt", "quá tốt", "đáng mua", "hài lòng", "ưng ý", "chất lượng", "mượt", "ổn định", "pin trâu", "sắc nét", "sang trọng", "rõ nét", "ngon"]
question_words = ["không ạ", "không nhỉ", "có không", "bao nhiêu", "thế nào", "khi nào", "tư vấn", "hỏi", "còn không", "còn hàng không", "còn k ạ", "shop còn", "có hàng không"]

def simple_sentiment(text):
    t = str(text).lower()
    if any(q in t for q in question_words):
        return "neutral"
    if any(n in t for n in strong_neg + neg_words):
        return "negative"
    if any(p in t for p in pos_words):
        return "positive"
    return "neutral"

def analyze_comments_sentiment(comments):
    if not comments:
        return {"pos": 0, "neu": 100, "neg": 0, "list": []}
    comments_clean = [str(c).strip() for c in comments if isinstance(c, (str, dict)) and str(c).strip()]
    if not comments_clean:
        return {"pos": 0, "neu": 100, "neg": 0, "list": []}
    sample = comments_clean[:50]
    stats = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
    results = []
    for text in sample:
        try:
            label = simple_sentiment(text)
            stats[label.upper()] += 1
            results.append({"text": text, "label": label.upper()})
        except Exception:
            continue
    total = len(results)
    if total == 0:
        return {"pos": 0, "neu": 100, "neg": 0, "list": []}
    return {
        "pos": round((stats["POSITIVE"] / total) * 100),
        "neu": round((stats["NEUTRAL"] / total) * 100),
        "neg": round((stats["NEGATIVE"] / total) * 100),
        "list": results
    }

# ---------------------------------------------------------------------------
# MongoDB data fetching
# ---------------------------------------------------------------------------
from pymongo import MongoClient

def extract_brand(name):
    if not name:
        return "unknown"
    name_low = name.lower()
    for b in BRANDS:
        if b in name_low:
            return b
    return "unknown"

def fetch_real_products(limit_per_collection=50):
    """Lấy sản phẩm thật từ MongoDB với price_history và comments."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    products = []
    for platform_name, col_name in STORE_COLLECTIONS.items():
        try:
            col = db[col_name]
            # Lấy tất cả sản phẩm, lọc sau ở Python vì MongoDB $exists đôi khi không ổn định với kiểu dữ liệu hỗn hợp
            cursor = col.find({}).limit(limit_per_collection * 3)
            count = 0
            for doc in cursor:
                comments = doc.get("comments")
                price_history = doc.get("price_history")
                # Chỉ lấy sản phẩm có ít nhất price_history HOẶC comments
                has_data = False
                if isinstance(price_history, list) and len(price_history) > 0:
                    has_data = True
                if isinstance(comments, list) and len(comments) > 0:
                    has_data = True
                if isinstance(comments, str) and comments.strip():
                    has_data = True
                if has_data:
                    doc["_platform"] = platform_name
                    products.append(doc)
                    count += 1
                    if count >= limit_per_collection:
                        break
        except Exception as e:
            print(f"⚠️ Lỗi đọc collection {col_name}: {e}")
    client.close()
    return products

# ---------------------------------------------------------------------------
# Evaluation on real data
# ---------------------------------------------------------------------------
def evaluate_on_real_data():
    print("=" * 80)
    print("ĐÁNH GIÁ PQS / RQS / RECOMMENDATION TRÊN DỮ LIỆU THỰC TẾ (MongoDB)")
    print("=" * 80)

    total_start = time.time()
    print("\n⏳ Đang kết nối MongoDB và lấy sản phẩm...")
    products = fetch_real_products(limit_per_collection=30)
    print(f"✅ Đã lấy {len(products)} sản phẩm từ {len(STORE_COLLECTIONS)} collection.")

    if not products:
        print("❌ Không có dữ liệu sản phẩm trong DB. Kết thúc.")
        return

    # Đánh giá từng sản phẩm
    results = []
    platform_counter = Counter()
    brand_counter = Counter()
    pqs_values = []
    rec_counter = Counter()
    label_counter = Counter()
    rqs_values = []
    comment_count_dist = []

    for doc in products:
        platform = doc.get("_platform", "Unknown")
        name = doc.get("name", "") or doc.get("title", "") or ""
        brand = extract_brand(name)
        comments = doc.get("comments", []) or []
        if isinstance(comments, str):
            comments = [comments]
        price_history = doc.get("price_history", []) or []
        price_number = doc.get("price_number", 0) or 0
        rating = doc.get("rating", 0) or 0

        # Parse price_history
        prices = []
        for entry in price_history:
            p = parse_price(entry.get("price", "")) if isinstance(entry, dict) else 0
            if p > 0:
                prices.append(p)
            elif isinstance(entry, (int, float)) and entry > 0:
                prices.append(int(entry))

        # Sentiment analysis
        sentiment_stats = analyze_comments_sentiment(comments)
        num_comments = len([c for c in comments if str(c).strip()])

        # Price stats
        price_stats = None
        if len(prices) >= 1:
            price_stats = {
                "min": int(min(prices)),
                "avg": int(sum(prices) / len(prices)),
                "max": int(max(prices)),
                "current": int(prices[-1]),
            }

        # Forecast price: nếu có đủ lịch sử, dùng heuristic đơn giản
        forecast_price = None
        if len(prices) >= 3:
            # Simple: giá trung bình 3 mốc gần nhất
            forecast_price = int(sum(prices[-3:]) / 3)

        # Current price: ưu tiên price_number, fallback giá cuối price_history
        current_price = price_number if price_number > 0 else (prices[-1] if prices else None)

        # Product dict cho calculate_pqs
        product_dict = {"name": name, "rating": rating}

        # PQS
        pqs = calculate_pqs(
            product_dict,
            sentiment_stats,
            current_price=current_price,
            forecast_price=forecast_price,
            min_market_price=price_stats["min"] if price_stats else None,
            max_market_price=price_stats["max"] if price_stats else None,
        )
        pqs_values.append(pqs)

        # Label
        label = get_pqs_label(pqs)

        # Price trend
        trend = get_price_trend(current_price, forecast_price)

        # Recommendation
        rec = get_buy_recommendation(pqs, price_stats, current_price, forecast_price)

        # RQS cho từng comment
        comment_rqs = []
        for c in comments[:20]:  # giới hạn 20 comment để không quá chậm
            c_text = str(c).strip() if not isinstance(c, dict) else str(c.get("text", c.get("content", ""))).strip()
            if not c_text:
                continue
            sent = simple_sentiment(c_text)
            rqs = calculate_rqs(c_text, sent.upper())
            comment_rqs.append({"text": c_text[:60], "sentiment": sent.upper(), "rqs": rqs})
            rqs_values.append(rqs)

        avg_rqs = round(sum(rqs_values) / len(rqs_values), 2) if rqs_values else 0

        # Đếm
        platform_counter[platform] += 1
        brand_counter[brand if brand else "unknown"] += 1
        rec_counter[rec["action"]] += 1
        label_counter[label["label"]] += 1
        comment_count_dist.append(num_comments)

        results.append({
            "platform": platform,
            "brand": brand,
            "name": name[:80],
            "price_number": price_number,
            "current_price": current_price,
            "price_stats": price_stats,
            "forecast_price": forecast_price,
            "rating": rating,
            "num_comments": num_comments,
            "sentiment_stats": sentiment_stats,
            "pqs": pqs,
            "pqs_label": label["label"],
            "trend": trend["trend"],
            "recommendation": rec["action"],
            "avg_rqs": avg_rqs,
            "comment_rqs_samples": comment_rqs[:5],
        })

    # -----------------------------------------------------------------------
    # Báo cáo thống kê
    # -----------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("BÁO CÁO THỐNG KÊ TRÊN DỮ LIỆU THỰC TẾ")
    print("=" * 80)

    print(f"\n📦 Tổng sản phẩm đánh giá: {len(results)}")
    print(f"   Số platform: {len(platform_counter)}")
    print(f"   Số brand: {len(brand_counter)}")

    print("\n--- Phân bố theo Platform ---")
    for p, c in platform_counter.most_common():
        print(f"   {p}: {c} sản phẩm")

    print("\n--- Phân bố theo Brand ---")
    for b, c in brand_counter.most_common(10):
        print(f"   {b}: {c}")

    print("\n--- Phân bố PQS ---")
    print(f"   Min PQS: {min(pqs_values)}")
    print(f"   Max PQS: {max(pqs_values)}")
    print(f"   Avg PQS: {sum(pqs_values)/len(pqs_values):.1f}")
    print(f"   Median PQS: {sorted(pqs_values)[len(pqs_values)//2]}")

    print("\n--- Phân bố Label PQS ---")
    for lbl, c in label_counter.most_common():
        print(f"   {lbl}: {c} ({c/len(results)*100:.1f}%)")

    print("\n--- Phân bố Recommendation ---")
    for rec_label, c in rec_counter.most_common():
        print(f"   {rec_label}: {c} ({c/len(results)*100:.1f}%)")

    print("\n--- Thống kê RQS ---")
    if rqs_values:
        print(f"   Min RQS: {min(rqs_values)}")
        print(f"   Max RQS: {max(rqs_values)}")
        print(f"   Avg RQS: {sum(rqs_values)/len(rqs_values):.2f}")
    else:
        print("   Không có comment để tính RQS.")

    print("\n--- Thống kê số comment ---")
    if comment_count_dist:
        print(f"   Min: {min(comment_count_dist)}")
        print(f"   Max: {max(comment_count_dist)}")
        print(f"   Avg: {sum(comment_count_dist)/len(comment_count_dist):.1f}")

    # Bảng top 10 sản phẩm có PQS cao nhất
    print("\n--- Top 10 sản phẩm PQS cao nhất ---")
    top10 = sorted(results, key=lambda x: x["pqs"], reverse=True)[:10]
    print(f"{'Platform':<20} {'Brand':<10} {'PQS':>5} {'Label':<25} {'Rec':<20} {'Trend':<12}")
    print("-" * 95)
    for item in top10:
        print(f"{item['platform']:<20} {item['brand']:<10} {item['pqs']:>5} {item['pqs_label']:<25} {item['recommendation']:<20} {item['trend']:<12}")

    # Bảng top 10 sản phẩm có PQS thấp nhất
    print("\n--- Top 10 sản phẩm PQS thấp nhất ---")
    bottom10 = sorted(results, key=lambda x: x["pqs"])[:10]
    print(f"{'Platform':<20} {'Brand':<10} {'PQS':>5} {'Label':<25} {'Rec':<20} {'Trend':<12}")
    print("-" * 95)
    for item in bottom10:
        print(f"{item['platform']:<20} {item['brand']:<10} {item['pqs']:>5} {item['pqs_label']:<25} {item['recommendation']:<20} {item['trend']:<12}")

    # Bảng vài sản phẩm có nhiều comment nhất
    print("\n--- Một số sản phẩm có nhiều comment nhất ---")
    most_commented = sorted(results, key=lambda x: x["num_comments"], reverse=True)[:5]
    print(f"{'Platform':<20} {'Name':<40} {'#Comments':>10} {'PQS':>5} {'Rec':<20}")
    print("-" * 100)
    for item in most_commented:
        print(f"{item['platform']:<20} {item['name'][:38]:<40} {item['num_comments']:>10} {item['pqs']:>5} {item['recommendation']:<20}")

    # Lưu JSON
    total_time = time.time() - total_start
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_products": len(results),
        "platforms": dict(platform_counter),
        "brands": dict(brand_counter),
        "pqs_stats": {
            "min": min(pqs_values),
            "max": max(pqs_values),
            "avg": round(sum(pqs_values)/len(pqs_values), 1),
            "median": sorted(pqs_values)[len(pqs_values)//2],
        },
        "label_distribution": dict(label_counter),
        "recommendation_distribution": dict(rec_counter),
        "rqs_stats": {
            "min": min(rqs_values) if rqs_values else 0,
            "max": max(rqs_values) if rqs_values else 0,
            "avg": round(sum(rqs_values)/len(rqs_values), 2) if rqs_values else 0,
        },
        "top10_pqs_high": [
            {"platform": i["platform"], "brand": i["brand"], "name": i["name"],
             "pqs": i["pqs"], "label": i["pqs_label"], "rec": i["recommendation"]}
            for i in top10
        ],
        "top10_pqs_low": [
            {"platform": i["platform"], "brand": i["brand"], "name": i["name"],
             "pqs": i["pqs"], "label": i["pqs_label"], "rec": i["recommendation"]}
            for i in bottom10
        ],
        "most_commented": [
            {"platform": i["platform"], "name": i["name"],
             "num_comments": i["num_comments"], "pqs": i["pqs"], "rec": i["recommendation"]}
            for i in most_commented
        ],
        "all_products": results,
        "total_time_seconds": round(total_time, 2),
    }

    report_path = os.path.join(BACKEND_DIR, "results", "evaluation_report_pqs_rqs_real_db.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Báo cáo chi tiết đã lưu tại: {report_path}")
    print(f"⏱️  Thời gian chạy: {total_time:.2f}s")


if __name__ == "__main__":
    evaluate_on_real_data()
