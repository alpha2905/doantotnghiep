# -*- coding: utf-8 -*-
"""
Script Đánh giá & So sánh Thực nghiệm (REAL PhoBERT inference, không dùng mô phỏng):
1. Rule-based Engine (Lexicon)
2. PhoBERT Standalone Model (Tải mô hình fine-tuned thực tế từ phobert_models/sentiment_classification/final_model)
3. Hybrid Engine (PhoBERT + Rule-based)

- Tập dữ liệu: phobert_train_sentiment_datn_balanced.jsonl
- Phân chia tập độc lập: 80% Train, 10% Validation, 10% Test Set
- Báo cáo: Accuracy, Per-class Precision/Recall/F1, Macro-F1, Weighted-F1, Ma trận nhầm lẫn
"""
import os
import sys
import json
import time

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MODEL_DIR = os.path.join(PROJECT_ROOT, "model", "phobert_models", "sentiment_classification", "final_model")

MAX_LENGTH = 128
BATCH_SIZE = 32
RANDOM_STATE = 42
TEST_SIZE = 0.10

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

CLASSES = ["positive", "neutral", "negative"]

# --- BỘ TỪ ĐIỂN TỪ KHÓA (RULE-BASED LEXICON) ---
strong_neg = ["hỏng", "lỗi", "tệ", "kém", "thất vọng", "lừa đảo", "hư", "trả hàng", "vỡ ảnh", "treo máy", "tắt nguồn", "crash", "bug", "mờ", "nóng quá", "chậm", "đơ", "lag"]
neg_words = ["đắt quá", "kém chất lượng", "tụt pin nhanh", "chai pin", "giật lag", "rè", "hết pin nhanh"]
pos_words = ["rất tốt", "cực tốt", "quá tốt", "đáng mua", "hài lòng", "ưng ý", "chất lượng", "mượt", "ổn định", "pin trâu", "sắc nét", "sang trọng", "rõ nét", "ngon"]
question_words = ["không ạ", "không nhỉ", "có không", "bao nhiêu", "thế nào", "khi nào", "tư vấn", "hỏi", "còn không", "còn hàng không", "còn k ạ", "shop còn", "có hàng không"]

def rule_based_sentiment(text):
    t = str(text).lower()
    if any(q in t for q in question_words):
        return "neutral"
    if any(n in t for n in strong_neg + neg_words):
        return "negative"
    if any(p in t for p in pos_words):
        return "positive"
    return "neutral"

def hybrid_sentiment(phobert_label, text):
    t = str(text).lower()
    if any(q in t for q in question_words):
        return "neutral"
    if any(n in t for n in strong_neg):
        return "negative"
    if any(p in t for p in pos_words) and not any(n in t for n in neg_words + strong_neg):
        return "positive"
    return phobert_label


class SentimentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            str(self.texts[idx]), truncation=True, padding='max_length',
            max_length=self.max_length, return_tensors='pt'
        )
        return {
            'input_ids': enc['input_ids'].flatten(),
            'attention_mask': enc['attention_mask'].flatten(),
            'label': torch.tensor(self.labels[idx], dtype=torch.long),
        }


def load_data():
    path = os.path.join(DATA_DIR, "phobert_train_sentiment_datn_balanced.jsonl")
    texts, labels = [], []
    label_map = {"positive": 0, "neutral": 1, "negative": 2, 1: 0, 2: 1, 0: 2}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    d = json.loads(line)
                    texts.append(d['text'])
                    lbl = d['label']
                    if isinstance(lbl, str) and lbl in label_map:
                        labels.append(label_map[lbl])
                    elif isinstance(lbl, int) and lbl in label_map:
                        labels.append(label_map[lbl])
                except Exception:
                    pass
    return texts, labels


def load_test_set():
    """Load test set cố định nếu có, ngược lại trả về None."""
    test_path = os.path.join(DATA_DIR, "sentiment_test_set.jsonl")
    if not os.path.exists(test_path):
        return None, None
    texts, labels = [], []
    label_map = {"positive": 0, "neutral": 1, "negative": 2}
    with open(test_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    d = json.loads(line)
                    texts.append(d['text'])
                    labels.append(d['label'])
                except Exception:
                    pass
    return texts, labels


def evaluate_engine(name, preds, trues, lat_ms):
    acc = accuracy_score(trues, preds)
    p, r, f1, support = precision_recall_fscore_support(trues, preds, average=None, zero_division=0)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(trues, preds, average='macro', zero_division=0)
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(trues, preds, average='weighted', zero_division=0)
    cm = confusion_matrix(trues, preds, labels=[0, 1, 2])

    print(f"\n--- {name} ---")
    print(f"• Latency/mẫu: {lat_ms:.2f} ms")
    print(f"• Accuracy: {acc*100:.2f}%")
    print(f"• Macro-F1: {macro_f1:.4f} | Weighted-F1: {weighted_f1:.4f}")
    print(f"• Macro-Precision: {macro_p:.4f} | Macro-Recall: {macro_r:.4f}")
    print(f"\n• Per-class metrics:")
    for i, cls in enumerate(CLASSES):
        print(f"  - {cls:10}: P={p[i]:.4f} R={r[i]:.4f} F1={f1[i]:.4f} (n={support[i]})")
    print(f"\n• Ma trận nhầm lẫn (Hàng=Thực tế, Cột=Dự đoán [POS, NEU, NEG]):\n{cm}")


def main():
    # Ưu tiên dùng Test Set cố định nếu có
    X_test, y_test = load_test_set()
    if X_test is not None:
        print(f"📌 Sử dụng Test Set cố định: {len(X_test)} mẫu")
        texts, labels = load_data()
        X_train_full, X_val, y_train_full, y_val = train_test_split(
            texts, labels, test_size=0.1111, random_state=RANDOM_STATE, stratify=labels
        )
    else:
        print("⚠️ Không tìm thấy Test Set cố định, sử dụng random split 80/10/10")
        texts, labels = load_data()
        X_train_full, X_test, y_train_full, y_test = train_test_split(
            texts, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=labels
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_full, y_train_full, test_size=1/9, random_state=RANDOM_STATE, stratify=y_train_full
        )
    
    idx2str = {0: "positive", 1: "neutral", 2: "negative"}
    str2idx = {"positive": 0, "neutral": 1, "negative": 2}
    
    # 1. ĐÁNH GIÁ RULE-BASED ENGINE
    t0 = time.time()
    rule_preds = [str2idx[rule_based_sentiment(t)] for t in X_test]
    lat_rule = (time.time() - t0) / len(X_test) * 1000
    evaluate_engine("1. Rule-based Engine (Lexicon)", rule_preds, y_test, lat_rule)

    # 2. ĐÁNH GIÁ PHOBERT STANDALONE (REAL INFERENCE)
    print(f"\n⏳ Đang tải mô hình PhoBERT Sentiment từ: {MODEL_DIR}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=False, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    test_ds = SentimentDataset(X_test, y_test, tokenizer, MAX_LENGTH)
    loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    phobert_preds = []
    t_pred = time.time()
    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(device)
            attn = batch['attention_mask'].to(device)
            logits = model(input_ids=input_ids, attention_mask=attn).logits
            phobert_preds.extend(torch.argmax(logits, dim=-1).cpu().tolist())
    lat_phobert = (time.time() - t_pred) / len(X_test) * 1000
    evaluate_engine("2. PhoBERT Standalone", phobert_preds, y_test, lat_phobert)

    # 3. ĐÁNH GIÁ HYBRID ENGINE (PHOBERT + RULE)
    t_hyb = time.time()
    hybrid_preds = []
    for t, p_idx in zip(X_test, phobert_preds):
        p_str = idx2str[p_idx]
        h_str = hybrid_sentiment(p_str, t)
        hybrid_preds.append(str2idx[h_str])
    lat_hybrid = lat_phobert + ((time.time() - t_hyb) / len(X_test) * 1000)
    evaluate_engine("3. Hybrid Engine (PhoBERT + Rule-based)", hybrid_preds, y_test, lat_hybrid)


if __name__ == "__main__":
    main()