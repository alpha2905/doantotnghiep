# -*- coding: utf-8 -*-
"""
Script Đánh giá Thực nghiệm Entity Resolution (Product Matching):
- Tạo tập Ground Truth gồm các cặp sản phẩm Cùng mẫu (Same Model) vs Khác mẫu/biến thể (Different Model/Variant).
- Kiểm thử độ nhạy ngưỡng tương đồng Cosine Similarity (0.60, 0.70, 0.75, 0.80, 0.85).
- Báo cáo chỉ số: Precision, Recall, F1-Score.
"""

import re
import sys
import os
import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import precision_recall_fscore_support

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

ground_truth_pairs = [
    # Cặp Positive (Cùng một sản phẩm)
    ("iPhone 16 Pro Max 256GB", "iPhone 16 Pro Max 256 GB Chính Hãng VN/A", True),
    ("Samsung Galaxy S24 Ultra 12GB 512GB", "Điện thoại Samsung Galaxy S24 Ultra 512GB", True),
    ("Xiaomi 14 Ultra 16GB 512GB", "Xiaomi 14 Ultra 512GB Chính hãng", True),
    ("OPPO Find X7 Ultra 256GB", "Điện thoại OPPO Find X7 Ultra 256GB", True),
    ("iPhone 15 Pro 128GB", "Apple iPhone 15 Pro 128GB VN/A", True),
    ("Samsung Galaxy Z Fold6 256GB", "Samsung Galaxy Z Fold 6 256GB 5G", True),
    ("Xiaomi Poco X6 Pro 5G 256GB", "POCO X6 Pro 5G 256GB Chính Hãng", True),
    ("iPhone 14 128GB", "iPhone 14 128GB VN/A Apple", True),
    ("Samsung Galaxy A55 5G 128GB", "Điện thoại Samsung Galaxy A55 5G 8GB/128GB", True),
    ("OPPO Reno11 Pro 5G 512GB", "OPPO Reno 11 Pro 5G 512GB", True),

    # Cặp Negative (Khác sản phẩm hoặc khác biến thể dung lượng)
    ("iPhone 16 Pro Max 256GB", "iPhone 16 Pro Max 512GB", False),
    ("iPhone 16 Pro Max 256GB", "iPhone 16 Pro 256GB", False),
    ("Samsung Galaxy S24 Ultra 256GB", "Samsung Galaxy S24 Plus 256GB", False),
    ("Samsung Galaxy S24 Ultra 256GB", "Samsung Galaxy S24 Ultra 512GB", False),
    ("Xiaomi 14 256GB", "Xiaomi 14 Ultra 512GB", False),
    ("iPhone 15 128GB", "iPhone 15 Plus 128GB", False),
    ("iPhone 15 Pro 128GB", "iPhone 15 Pro Max 256GB", False),
    ("OPPO Reno11 256GB", "OPPO Reno11 Pro 512GB", False),
    ("Samsung Galaxy Z Flip6 256GB", "Samsung Galaxy Z Fold6 256GB", False),
    ("Xiaomi Redmi Note 13 128GB", "Xiaomi Redmi Note 13 Pro 256GB", False),
]

def clean_title(title):
    t = str(title).lower()
    t = re.sub(r'(điện thoại|chính hãng|vn/a|apple|5g|8gb/|12gb/|16gb/)', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def calculate_similarity(name1, name2):
    c1, c2 = clean_title(name1), clean_title(name2)
    
    # Kiểm tra mismatch dung lượng (ví dụ: 256GB vs 512GB)
    capacities = ["128gb", "256gb", "512gb", "1tb"]
    cap1 = next((c for c in capacities if c in name1.lower()), None)
    cap2 = next((c for c in capacities if c in name2.lower()), None)
    if cap1 and cap2 and cap1 != cap2:
        return 0.0

    vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
    tfidf = vectorizer.fit_transform([c1, c2])
    sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    return sim

# Ngưỡng operam tối ưu được lựa chọn cho bài toán Entity Resolution
ENTITY_MATCH_THRESHOLD = 0.80

def is_match(name1, name2, threshold=ENTITY_MATCH_THRESHOLD):
    """Dự đoán khả năng ghép nối trùng khớp giữa 2 tên sản phẩm tại ngưỡng chỉ định (mặc định 0.80)."""
    return calculate_similarity(name1, name2) >= threshold

def evaluate_entity_resolution():
    print(f"\n==========================================================================")
    print(f"🔍 THỰC NGHIỆM ĐÁNH GIÁ ENTITY RESOLUTION (PRODUCT MATCHING THRESHOLD)")
    print(f"==========================================================================")
    print(f"Tổng số cặp sản phẩm Ground Truth: {len(ground_truth_pairs)}")
    
    # Phân tích ground truth
    pos_pairs = [p for p in ground_truth_pairs if p[2]]
    neg_pairs = [p for p in ground_truth_pairs if not p[2]]
    print(f"  - Cặp cùng sản phẩm (Positive): {len(pos_pairs)}")
    print(f"  - Cặp khác sản phẩm (Negative): {len(neg_pairs)}")

    thresholds = [0.60, 0.70, 0.75, 0.80, 0.85]
    results = []

    for th in thresholds:
        y_true = []
        y_pred = []
        similarities = []
        
        for name1, name2, is_same in ground_truth_pairs:
            sim = calculate_similarity(name1, name2)
            pred = sim >= th
            y_true.append(is_same)
            y_pred.append(pred)
            similarities.append(sim)

        p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
        results.append({
            "Cosine Threshold": f"{th:.2f}",
            "Precision": f"{p:.4f}",
            "Recall": f"{r:.4f}",
            "F1-Score": f"{f1:.4f}",
            "Avg Similarity": f"{np.mean(similarities):.4f}"
        })

    df_res = pd.DataFrame(results)
    print("\n--- KẾT QUẢ ĐÁNH GIÁ NGƯỠNG TƯƠNG ĐỒNG ENTITY RESOLUTION ---")
    print(df_res.to_string(index=False))

    # Lựa chọn ngưỡng tối ưu (Đạt F1-Score cao nhất)
    best = max(results, key=lambda r: float(r["F1-Score"]))
    print("\n🔎 NGƯỠNG TỐI ƯU (Đạt F1-Score cao nhất):", best["Cosine Threshold"])
    print(f"   => Precision {best['Precision']} | Recall {best['Recall']} | F1-Score {best['F1-Score']}")
    
    # Phân tích các trường hợp khó (near-threshold cases)
    print("\n[Phân tích các trường hợp khó - near threshold]")
    threshold = ENTITY_MATCH_THRESHOLD
    for name1, name2, is_same in ground_truth_pairs:
        sim = calculate_similarity(name1, name2)
        if abs(sim - threshold) < 0.1:  # Near threshold
            pred = sim >= threshold
            status = "✓" if pred == is_same else "✗"
            print(f"  {status} sim={sim:.3f} (threshold={threshold}): '{name1[:40]}' vs '{name2[:40]}'")

    # Ngưỡng vận hành thực tế được cấu hình trong hệ thống = 0.80
    print(f"\n✅ NGƯỠNG VẬN HÀNH TRONG HỆ THỐNG: {ENTITY_MATCH_THRESHOLD:.2f}")
    op = next((r for r in results if float(r['Cosine Threshold']) == ENTITY_MATCH_THRESHOLD), None)
    if op:
        print(f"   (Xác nhận chỉ số tại ngưỡng {ENTITY_MATCH_THRESHOLD:.2f}: "
              f"Precision {op['Precision']} | Recall {op['Recall']} | F1-Score {op['F1-Score']})")
    
    # Lưu kết quả chi tiết
    import json
    results_path = os.path.join(os.path.dirname(__file__), os.pardir, "results", "entity_resolution_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump({
            "ground_truth_pairs": len(ground_truth_pairs),
            "positive_pairs": len(pos_pairs),
            "negative_pairs": len(neg_pairs),
            "thresholds_tested": thresholds,
            "results": results,
            "optimal_threshold": best["Cosine Threshold"],
            "optimal_f1": best["F1-Score"],
            "operating_threshold": ENTITY_MATCH_THRESHOLD
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Kết quả đã lưu: {results_path}")

if __name__ == "__main__":
    evaluate_entity_resolution()