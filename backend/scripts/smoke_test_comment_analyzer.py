# -*- coding: utf-8 -*-
"""Smoke test cho comment_analyzer (hybrid PhoBERT + rule-based).

Cách dùng:
    python backend/scripts/smoke_test_comment_analyzer.py             # nạp PhoBERT thật
    python backend/scripts/smoke_test_comment_analyzer.py --no-model  # chỉ rule-based (nhanh)

Kiểm tra: phân bố cảm xúc, khía cạnh, engine nào quyết định (source), confidence, latency.
"""
import argparse
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BACKEND_DIR)

import comment_analyzer as CA  # noqa: E402

SENT_DIR = os.path.join(BACKEND_DIR, "model", "phobert_models", "sentiment_classification", "final_model")
ASPECT_DIR = os.path.join(BACKEND_DIR, "model", "phobert_models", "aspect_classification", "final_model")

SAMPLE_COMMENTS = [
    "Pin trâu dùng được 2 ngày, rất hài lòng",
    "Máy nóng quá, tụt pin nhanh, thất vọng",
    "Shop còn hàng không ạ",
    "Camera chụp đêm đẹp nét, ảnh rõ",
    "Màn hình sắc nét nhưng loa hơi rè",
    "Giá đắt quá so với cấu hình",
    "Mượt mà, chơi game không giật, đáng mua",
    "Giao hàng nhanh, nhân viên tư vấn nhiệt tình",
]


def load_models():
    """Nạp PhoBERT sentiment + aspect (trả về (tokenizer, model_sent, model_aspect))."""
    import torch
    from transformers import AutoTokenizer, RobertaForSequenceClassification

    for path in (SENT_DIR, ASPECT_DIR):
        if not os.path.exists(path):
            print(f"⚠️  Không thấy model tại: {path}")
            return None, None, None

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(SENT_DIR, use_fast=False, local_files_only=True)
    model_sent = RobertaForSequenceClassification.from_pretrained(SENT_DIR, local_files_only=True)
    model_aspect = RobertaForSequenceClassification.from_pretrained(ASPECT_DIR, local_files_only=True)
    model_sent.eval()
    model_aspect.eval()
    print(f"✅ Đã nạp PhoBERT sentiment + aspect trong {time.time() - t0:.1f}s")
    print(f"   device: {next(model_sent.parameters()).device}")
    return tokenizer, model_sent, model_aspect


def main():
    parser = argparse.ArgumentParser(description="Smoke test comment_analyzer")
    parser.add_argument("--no-model", action="store_true", help="Chỉ chạy rule-based (không nạp PhoBERT)")
    args = parser.parse_args()

    print("=" * 78)
    print("SMOKE TEST: comment_analyzer (PhoBERT + rule-based hybrid)")
    print("=" * 78)

    tokenizer = model_sent = model_aspect = None
    if not args.no_model:
        try:
            tokenizer, model_sent, model_aspect = load_models()
        except Exception as e:
            print(f"⚠️  Không nạp được PhoBERT ({e}) -> chạy rule-based")
    if model_sent is None:
        print("ℹ️  Chế độ rule-based (không có PhoBERT)")

    # ⚠️ Bắt buộc đọc label_mapping.json: model fine-tune lưu 0=negative, 1=neutral, 2=positive
    sent_map, asp_map, sources = CA.load_label_maps(SENT_DIR, ASPECT_DIR)
    print(f"🏷️  Ánh xạ nhãn cảm xúc: {sent_map}")
    print(f"🏷️  Nguồn ánh xạ: {sources}")

    t0 = time.time()
    result = CA.analyze_comments(SAMPLE_COMMENTS, tokenizer, model_sent, model_aspect,
                                 sentiment_map=sent_map, aspect_map=asp_map, label_sources=sources)
    elapsed = time.time() - t0

    print(f"\n📊 Phân bố cảm xúc: POS {result['pos']}% | NEU {result['neu']}% | NEG {result['neg']}%"
          f"  (n={result['total']})")
    print(f"🧠 Engine quyết định: {result['engine_stats']}")
    print(f"🎯 Confidence trung bình: {result['average_confidence']}")
    print(f"⏱️  Latency API nội bộ: {result['latency_ms']} ms (bao gồm {elapsed:.2f}s overhead bên ngoài)")

    print("\n📈 Phân bố khía cạnh:")
    for item in result["aspects"]:
        print(f"   - {item['aspect']:<14} {item['count']:>3} ({item['percent']}%)")

    print("\n📝 Chi tiết từng bình luận:")
    for c in result["list"]:
        conf = f"{c['confidence']:.2f}" if c["confidence"] is not None else "  - "
        print(f"   [{c['label']:<8}] src={c['source']:<13} conf={conf} aspect={c['aspect']:<14} "
              f"rqs={c['rqs']} | {c['text'][:52]}")

    print("\n" + "=" * 78)
    print(f"NOTE: {result['note']}")
    print("=" * 78)


if __name__ == "__main__":
    main()
