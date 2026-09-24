# -*- coding: utf-8 -*-
"""
comment_analyzer.py — PhoBERT + Rule-based Hybrid Analyzer cho bình luận TMĐT

Vì sao tách riêng module này (docs/REWRITE_PLAN.md - Requirement 12):
- main.py (FastAPI) và background_workers.py cần DÙNG CHUNG một logic phân tích
  (trước đây background worker chỉ có placeholder, kết quả PQS/RQS bị lệch nhau).
- Bổ sung thông tin phục vụ bảo vệ/minh bạch mô hình:
    * source          : "phobert" | "rule" | "rule_fallback"  (engine nào quyết định nhãn)
    * confidence      : xác suất softmax của nhãn được chọn
    * aspect_source   : "rule" | "phobert"
    * engine_stats    : số bình luận do từng engine quyết định
    * aspects         : phân bố khía cạnh (%)
- Suy luận THEO BATCH (thay vì từng câu) để giảm latency khi phân tích 50 bình luận.
"""
import json
import os
import time

import torch

MODEL_ID = "vinai/phobert-base-v2"

# ⚠️ ÁNH XẠ NHÃN (bug đã sửa): model fine-tune lưu thứ tự nhãn trong label_mapping.json.
# train_phobert_from_labeled.py tạo nhãn bằng sorted(set(labels)) -> negative=0, neutral=1, positive=2.
# Trước đây main.py hardcode 0=POSITIVE / 2=NEGATIVE nên TOÀN BỘ nhãn PhoBERT bị ĐẢO NGƯỢC.
# => Luôn ưu tiên đọc label_mapping.json (xem load_label_maps); giá trị dưới đây là fallback đúng.
SENTIMENT_BY_INDEX = {0: "NEGATIVE", 1: "NEUTRAL", 2: "POSITIVE"}
LABEL_MAPPING_FILE = "label_mapping.json"
SENTIMENT_CONF_THRESHOLD = 0.55  # dưới ngưỡng này coi như model "không chắc" -> để rule-based quyết định

ASPECT_LABELS = [
    "bảo_mật", "camera", "giá", "hiệu_năng", "hệ_điều_hành",
    "khác", "loa_âm_thanh", "màn_hình", "pin", "thiết_kế",
]

QUESTION_WORDS = [
    "không ạ", "không nhỉ", "có không", "bao nhiêu", "thế nào",
    "khi nào", "tư vấn", "hỏi", "còn không", "còn hàng không",
    "còn k ạ", "shop còn", "có hàng không",
]

STRONG_NEGATIVE = [
    "hỏng", "lỗi", "tệ", "kém", "thất vọng", "lừa đảo",
    "hư", "trả hàng", "vỡ ảnh", "treo máy", "tắt nguồn",
    "crash", "bug", "mờ", "nóng quá", "chậm", "đơ", "lag",
]

NEGATIVE_WORDS = [
    "đắt quá", "kém chất lượng", "tụt pin nhanh", "chai pin",
    "giật lag", "rè", "hết pin nhanh",
]

POSITIVE_WORDS = [
    "rất tốt", "cực tốt", "quá tốt", "đáng mua", "hài lòng",
    "ưng ý", "chất lượng", "mượt", "ổn định",
    "pin trâu", "sắc nét", "sang trọng", "rõ nét", "ngon",
    "tốt", "ok", "được", "ưng", "xài ổn", "nhiều tính năng",
    "đáng tiền", "hoàn thiện", "bền", "đáng đồng tiền", "thoải mái",
    "không có lỗi", "ngon bổ rẻ", "mượt mà", "nhanh nhạy", "tốt trong phân khúc",
]

# Từ điển khía cạnh: SẮP XẾP THEO ĐỘ ƯU TIÊN (cụm dài trước) — copy nguyên trạng từ main.py
ASPECT_KEYWORDS = [
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

    # LOA ÂM THANH — để sau cùng vì "loa" dễ match nhầm
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
]


# ============================================================
# 1. RULE-BASED ENGINE (Lexicon)
# ============================================================
def load_label_maps(sentiment_dir=None, aspect_dir=None):
    """Đọc label_mapping.json của 2 model -> (sentiment_map, aspect_map, sources).

    sentiment_map: {idx: 'POSITIVE'|'NEUTRAL'|'NEGATIVE'}
    aspect_map:    {idx: 'camera'|'giá'|...}  (label_mapping của aspect lưu dạng label->idx)
    """
    sent_map = dict(SENTIMENT_BY_INDEX)
    asp_map = {i: label for i, label in enumerate(ASPECT_LABELS)}
    sources = {"sentiment": "default(SENTIMENT_BY_INDEX)", "aspect": "default(ASPECT_LABELS)"}

    if sentiment_dir:
        path = os.path.join(sentiment_dir, LABEL_MAPPING_FILE)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            sent_map = {int(k): str(v).upper() for k, v in raw.items()}
            sources["sentiment"] = path
        except Exception as e:
            print(f"[comment_analyzer] Không đọc được {path} ({e}) -> dùng ánh xạ mặc định")

    if aspect_dir:
        path = os.path.join(aspect_dir, LABEL_MAPPING_FILE)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if raw and all(isinstance(v, int) for v in raw.values()):
                asp_map = {int(v): str(k) for k, v in raw.items()}   # label -> idx
            else:
                asp_map = {int(k): str(v) for k, v in raw.items()}   # idx -> label
            sources["aspect"] = path
        except Exception as e:
            print(f"[comment_analyzer] Không đọc được {path} ({e}) -> dùng ánh xạ mặc định")

    return sent_map, asp_map, sources


def rule_sentiment(text_low):
    """Nhãn cảm xúc theo luật từ khoá. Trả về None nếu luật không quyết định được."""
    if any(q in text_low for q in QUESTION_WORDS):
        return "NEUTRAL"
    if any(n in text_low for n in STRONG_NEGATIVE + NEGATIVE_WORDS):
        return "NEGATIVE"
    if any(p in text_low for p in POSITIVE_WORDS):
        return "POSITIVE"
    return None


def rule_aspect(text_low):
    """Khía cạnh theo luật từ khoá (ưu tiên tuyệt đối vì chính xác hơn cho từ vựng TMĐT)."""
    for keyword, aspect in ASPECT_KEYWORDS:
        if keyword in text_low:
            return aspect
    return None


def calculate_rqs(comment_text, sentiment_label):
    """RQS = Review Quality Score (thang 5).

    RQS = điểm cảm xúc + điểm độ dài (bình luận càng chi tiết càng hữu ích).
    """
    if not comment_text:
        return 0

    text = str(comment_text).strip()
    length = len(text)

    if sentiment_label == "POSITIVE":
        sent_score = 4.0
    elif sentiment_label == "NEGATIVE":
        sent_score = 2.0
    else:
        sent_score = 3.0

    if length >= 100:
        length_score = 1.0
    elif length >= 50:
        length_score = 0.7
    elif length >= 20:
        length_score = 0.4
    else:
        length_score = 0.1

    return round(min(5.0, sent_score + length_score), 1)


def empty_sentiment():
    """Payload rỗng (khi chưa bật phân tích AI / sản phẩm không có bình luận)."""
    return {
        "pos": 0, "neu": 100, "neg": 0, "pos_count": 0, "total": 0, "list": [],
        "aspects": [], "engine_stats": {"phobert": 0, "rule": 0, "rule_fallback": 0},
        "conflict_count": 0, "conflict_rate": 0.0, "conflict_examples": [],
        "average_confidence": 0.0, "analyzed_count": 0, "sample_limit": 0,
        "model_id": MODEL_ID, "model_loaded": False,
        "note": "Chưa có bình luận hoặc chưa chạy phân tích AI.",
    }


def _comment_texts(comments):
    """Chuẩn hoá + khử trùng lặp (giữ thứ tự) danh sách bình luận thô."""
    texts = []
    seen = set()
    for c in comments or []:
        if isinstance(c, dict):
            raw = c.get("text") or c.get("content") or c.get("comment") or ""
        else:
            raw = c
        text = str(raw).strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        texts.append(text)
    return texts


# ============================================================
# 2. PHOBERT BATCH INFERENCE
# ============================================================
def _model_device(model):
    try:
        return next(model.parameters()).device
    except Exception:
        return torch.device("cpu")


def _softmax_confidence(logits, index):
    """Xác suất softmax của nhãn được chọn (0..1). None nếu không tính được."""
    try:
        probs = torch.softmax(logits, dim=-1)
        return float(probs[0][index])
    except Exception:
        return None


def infer_batch(texts, tokenizer, model_sent, model_aspect=None, batch_size=16, max_length=128):
    """Suy luận PhoBERT theo batch.

    Trả về list các dict: {'sent_idx','sent_conf','aspect_idx','aspect_conf','ok'}.
    Batch inference giúp giảm latency so với chạy từng câu (trước đây 50 câu = 50 forward pass).
    """
    n = len(texts)
    out = [{"sent_idx": None, "sent_conf": None, "aspect_idx": None, "aspect_conf": None, "ok": False}
           for _ in range(n)]
    if tokenizer is None or model_sent is None or n == 0:
        return out

    device = _model_device(model_sent)
    model_sent.eval()
    if model_aspect is not None:
        model_aspect.eval()

    for start in range(0, n, batch_size):
        chunk = texts[start:start + batch_size]
        try:
            enc = tokenizer(chunk, return_tensors="pt", truncation=True,
                            max_length=max_length, padding=True)
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.no_grad():
                sent_logits = model_sent(**enc).logits
                aspect_logits = model_aspect(**enc).logits if model_aspect is not None else None
        except Exception as e:
            print(f"[comment_analyzer] Lỗi suy luận PhoBERT (batch bắt đầu {start}): {e}")
            continue

        for j in range(len(chunk)):
            sent_idx = int(torch.argmax(sent_logits[j], dim=-1).item())
            item = {
                "sent_idx": sent_idx,
                "sent_conf": _softmax_confidence(sent_logits[j].unsqueeze(0), sent_idx),
                "aspect_idx": None,
                "aspect_conf": None,
                "ok": True,
            }
            if aspect_logits is not None:
                aspect_idx = int(torch.argmax(aspect_logits[j], dim=-1).item())
                item["aspect_idx"] = aspect_idx
                item["aspect_conf"] = _softmax_confidence(aspect_logits[j].unsqueeze(0), aspect_idx)
            out[start + j] = item
    return out


# ============================================================
# 3. HYBRID ANALYZER (PUBLIC API)
# ============================================================
def analyze_comments(comments, tokenizer=None, model_sent=None, model_aspect=None,
                     sample_limit=50, batch_size=16, max_length=128,
                     sentiment_map=None, aspect_map=None, label_sources=None):
    """Phân tích cảm xúc + khía cạnh cho danh sách bình luận (hybrid PhoBERT + rule-based).

    Thứ tự quyết định (ghi lại ở field `source` của từng bình luận):
    1. Câu hỏi mua hàng (question words)        -> NEUTRAL, source="rule"/"rule_fallback"
    2. PhoBERT không chạy / lỗi                 -> rule-based, source="rule_fallback"
    3. PhoBERT trả NEUTRAL hoặc confidence thấp -> rule-based ghi đè nếu có, source="rule"
    4. Còn lại                                  -> theo PhoBERT, source="phobert"

    Khía cạnh: rule-based ưu tiên tuyệt đối (chính xác hơn cho từ vựng TMĐT), PhoBERT là fallback.
    `sentiment_map`/`aspect_map` lấy từ label_mapping.json (bắt buộc đúng thứ tự nhãn của model).
    """
    t0 = time.time()
    sent_map = sentiment_map or SENTIMENT_BY_INDEX
    asp_map = aspect_map or {i: label for i, label in enumerate(ASPECT_LABELS)}
    texts = _comment_texts(comments)
    if not texts:
        out = empty_sentiment()
        out["model_loaded"] = model_sent is not None
        out["latency_ms"] = 0
        return out

    sample = texts[:int(sample_limit)]
    model_loaded = tokenizer is not None and model_sent is not None
    preds = (infer_batch(sample, tokenizer, model_sent, model_aspect,
                         batch_size=batch_size, max_length=max_length)
             if model_loaded else [None] * len(sample))

    counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
    engine_stats = {"phobert": 0, "rule": 0, "rule_fallback": 0}
    aspect_counts = {}
    confidences = []
    results = []
    conflict_count = 0
    conflict_examples = []

    for text, pred in zip(sample, preds):
        text_low = text.lower()
        model_ok = bool(pred and pred.get("ok"))
        model_label = sent_map.get(pred["sent_idx"]) if model_ok else None
        model_conf = pred.get("sent_conf") if model_ok else None

        # --- Quyết định nhãn: giống hybrid_sentiment() trong evaluate_phobert_hybrid.py
        # để hành vi runtime KHỚP với số liệu thực nghiệm đã báo cáo.
        is_question = any(q in text_low for q in QUESTION_WORDS)
        has_negative = any(n in text_low for n in STRONG_NEGATIVE + NEGATIVE_WORDS)
        has_positive = any(p in text_low for p in POSITIVE_WORDS)

        if is_question:
            label, source = "NEUTRAL", ("rule" if model_ok else "rule_fallback")
        elif has_negative:
            label, source = "NEGATIVE", ("rule" if model_ok else "rule_fallback")
        elif has_positive:
            label, source = "POSITIVE", ("rule" if model_ok else "rule_fallback")
        elif model_ok:
            label, source = model_label, "phobert"
        else:
            label, source = "NEUTRAL", "rule_fallback"

        # Xung đột rule-based vs PhoBERT (dùng cho error analysis trên UI/báo cáo)
        conflict = bool(model_ok and model_label != label)
        if conflict and len(conflict_examples) < 5:
            conflict_examples.append({
                "text": text,
                "final_label": label,
                "engine": source,
                "phobert_label": model_label,
                "phobert_confidence": round(model_conf, 3) if model_conf is not None else None,
            })

        if conflict:
            conflict_count += 1

        # --- Khía cạnh: rule trước, PhoBERT fallback ---
        aspect = rule_aspect(text_low)
        aspect_source = "rule"
        if aspect is None:
            a_idx = pred.get("aspect_idx") if model_ok else None
            if a_idx is not None and a_idx in asp_map:
                aspect = asp_map[a_idx]
                aspect_source = "phobert"
            else:
                aspect = "khác"
                aspect_source = "rule"

        # confidence = độ tự tin của PhoBERT cho nhãn do CHÍNH model dự đoán
        # (vẫn ghi lại khi rule-based ghi đè -> phục vụ phân tích xung đột)
        confidence = model_conf
        if confidence is not None:
            confidences.append(confidence)
        counts[label] += 1
        engine_stats[source] = engine_stats.get(source, 0) + 1
        aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1

        results.append({
            "text": text,
            "label": label,
            "aspect": aspect,
            "aspect_source": aspect_source,
            "source": source,
            "confidence": round(confidence, 3) if confidence is not None else None,
            "phobert_label": model_label,
            "conflict": conflict,
            "rqs": calculate_rqs(text, label),
        })

    total = len(results)
    if total == 0:
        out = empty_sentiment()
        out["model_loaded"] = model_loaded
        return out

    aspects = [
        {"aspect": k, "count": v, "percent": round(v / total * 100, 1)}
        for k, v in sorted(aspect_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    latency_ms = round((time.time() - t0) * 1000, 1)

    return {
        "pos": round(counts["POSITIVE"] / total * 100),
        "neu": round(counts["NEUTRAL"] / total * 100),
        "neg": round(counts["NEGATIVE"] / total * 100),
        "pos_count": counts["POSITIVE"],
        "neg_count": counts["NEGATIVE"],
        "neu_count": counts["NEUTRAL"],
        "total": total,
        "list": results,
        "aspects": aspects,
        "engine_stats": engine_stats,
        "conflict_count": conflict_count,
        "conflict_rate": round(conflict_count / total * 100, 1),
        "conflict_examples": conflict_examples,
        "average_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
        "analyzed_count": total,
        "sample_limit": int(sample_limit),
        "all_comments_count": len(texts),
        "model_id": MODEL_ID,
        "model_loaded": model_loaded,
        "latency_ms": latency_ms,
        "sentiment_label_map": {str(k): v for k, v in sent_map.items()},
        "label_map_sources": label_sources or {},
        "note": (
            f"Phân tích {total}/{len(texts)} bình luận (tối đa {int(sample_limit)}) bằng hybrid engine "
            f"(PhoBERT {MODEL_ID} + rule-based)."
        ),
    }


def get_analyzer_meta(model_sent=None):
    """Thông tin mô hình cho dashboard/UI (model id, ngưỡng confidence, số luật rule-based)."""
    return {
        "model_id": MODEL_ID,
        "model_loaded": model_sent is not None,
        "confidence_threshold": SENTIMENT_CONF_THRESHOLD,
        "aspect_labels": ASPECT_LABELS,
        "sentiment_labels": ["POSITIVE", "NEUTRAL", "NEGATIVE"],
        "rule_keywords": {
            "question": len(QUESTION_WORDS),
            "strong_negative": len(STRONG_NEGATIVE),
            "negative": len(NEGATIVE_WORDS),
            "positive": len(POSITIVE_WORDS),
            "aspect_rules": len(ASPECT_KEYWORDS),
        },
        "note": (
            "Hybrid engine: rule-based quyết định với câu hỏi/từ khoá mạnh; PhoBERT quyết định "
            "khi model đủ tự tin; xung đột được ghi lại ở field source của từng bình luận."
        ),
    }




