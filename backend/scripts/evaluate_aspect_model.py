# -*- coding: utf-8 -*-
"""
Script Đánh giá Model PhoBERT fine-tuned: ASPECT CLASSIFICATION (10 lớp).
- Đọc phobert_train_aspect.jsonl
- Phân chia Stratify: 80% Train / 10% Val / 10% Test
- Tính toán Accuracy, per-class Precision/Recall/F1, Macro/Weighted-F1, Confusion Matrix
"""
import os
import sys
import json
import time
from collections import Counter

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, classification_report
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MODEL_DIR = os.path.join(PROJECT_ROOT, "model", "phobert_models", "aspect_classification", "final_model")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

MAX_LENGTH = 128
BATCH_SIZE = 32
RANDOM_STATE = 42

# Sửa lỗi: Đổi TEST_SIZE từ 0.025 thành 0.10 để tập Test đạt chính xác 10% (~577 mẫu)
TEST_SIZE = 0.10  

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load


class AspectDataset(Dataset):
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
    path = os.path.join(DATA_DIR, "phobert_train_aspect.jsonl")
    texts, labels = [], []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    d = json.loads(line)
                    texts.append(d['text'])
                    labels.append(d['label'])
                except Exception:
                    pass
    return texts, labels


def load_test_set():
    """Load test set cố định nếu có, ngược lại trả về None."""
    test_path = os.path.join(DATA_DIR, "aspect_test_set.jsonl")
    if not os.path.exists(test_path):
        return None, None
    texts, labels = [], []
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


def main():
    mapping_path = os.path.join(PROJECT_ROOT, "model", "phobert_models", "aspect_classification", "label_mapping.json")
    with open(mapping_path, encoding='utf-8') as f:
        label_mapping = json.load(f)          # label -> idx
    
    idx2label = {v: k for k, v in label_mapping.items()}
    classes = [idx2label[i] for i in sorted(idx2label.keys())]

    texts, labels = load_data()

    # Ưu tiên dùng Test Set cố định nếu có
    X_test, y_test_str = load_test_set()
    if X_test is not None:
        print(f"📌 Sử dụng Aspect Test Set cố định: {len(X_test)} mẫu")
        label_mapping_rev = {v: k for k, v in label_mapping.items()}
        y_test = [label_mapping.get(lbl, 0) for lbl in y_test_str]
        texts_filtered, labels_filtered = [], []
        for t, l in zip(texts, labels):
            if l in label_mapping:
                texts_filtered.append(t)
                labels_filtered.append(label_mapping[l])
        X_train_full, X_val, y_train_full, y_val = train_test_split(
            texts_filtered, labels_filtered, test_size=0.1111,
            random_state=RANDOM_STATE, stratify=labels_filtered
        )
    else:
        print("⚠️ Không tìm thấy Aspect Test Set cố định, sử dụng random split 80/10/10")
        filtered_texts, filtered_labels = [], []
        for t, l in zip(texts, labels):
            if l in label_mapping:
                filtered_texts.append(t)
                filtered_labels.append(label_mapping[l])
        X_train_full, X_test, y_train_full, y_test = train_test_split(
            filtered_texts, filtered_labels, test_size=TEST_SIZE,
            random_state=RANDOM_STATE, stratify=filtered_labels
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_full, y_train_full, test_size=0.1111,
            random_state=RANDOM_STATE, stratify=y_train_full
        )

    test_dist = Counter(y_test)
    print(f"\n[Phân chia Tập dữ liệu] Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
    print("[Phân bố các lớp trong Tập Test]")
    for i in sorted(idx2label.keys()):
        print(f"  {idx2label[i]:16} {test_dist.get(i,0):5,}")

    print(f"\n⏳ Đang tải mô hình PhoBERT Aspect từ: {MODEL_DIR}")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=False, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR, local_files_only=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"✅ Mô hình đã tải xong trong {time.time()-t0:.1f}s (Thiết bị={device})")

    test_ds = AspectDataset(X_test, y_test, tokenizer, MAX_LENGTH)
    loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    preds, trues = [], []
    t_pred = time.time()
    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(device)
            attn = batch['attention_mask'].to(device)
            logits = model(input_ids=input_ids, attention_mask=attn).logits
            preds.extend(torch.argmax(logits, dim=-1).cpu().tolist())
            trues.extend(batch['label'].tolist())
    lat_ms = (time.time() - t_pred) / len(X_test) * 1000

    acc = accuracy_score(trues, preds)
    p, r, f1, _ = precision_recall_fscore_support(trues, preds, average='weighted', zero_division=0)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(trues, preds, average='macro', zero_division=0)
    cp, cr, cf, cs = precision_recall_fscore_support(trues, preds, labels=list(range(len(classes))), zero_division=0)
    cm = confusion_matrix(trues, preds, labels=list(range(len(classes))))

    print(f"\n{'='*78}")
    print("=== KẾT QUẢ ASPECT CLASSIFICATION (Model PhoBERT fine-tuned, local) ===")
    print(f"{'='*78}")
    print(f"• Latency/sample: {lat_ms:.2f} ms")
    print(f"• Accuracy: {acc*100:.2f}%")
    print(f"• Macro avg   | Precision: {macro_p:.4f} | Recall: {macro_r:.4f} | F1: {macro_f1:.4f}")
    print(f"• Weighted avg| Precision: {p:.4f} | Recall: {r:.4f} | F1: {f1:.4f}")
    print("\n--- Precision / Recall / F1 Chi tiết từng Lớp ---")
    print(f"{'Khía cạnh':16} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Số mẫu':>9} {'Tỷ lệ':>8}")
    for i in range(len(classes)):
        pct = cs[i] / total * 100 if total > 0 else 0
        print(f"{classes[i]:16} {cp[i]:8.4f} {cr[i]:8.4f} {cf[i]:8.4f} {cs[i]:9,} {pct:7.2f}%")
    
    print(f"\n[Phân tích mất cân bằng]")
    print(f"  - Macro-F1: {macro_f1:.4f} (quan tâm đến tất cả các lớp)")
    print(f"  - Weighted-F1: {f1:.4f} (quan tâm đến lớp đa số)")
    print(f"  - Chênh lệch: {abs(macro_f1 - f1):.4f} (càng lớn càng mất cân bằng)")
    if macro_f1 < f1:
        print("  ⚠️ Weighted-F1 > Macro-F1: mô hình thiên về lớp đa số")
    elif macro_f1 > f1:
        print("  ✅ Macro-F1 > Weighted-F1: mô hình học tốt cả lớp thiểu số")
    else:
        print("  ➡️ Macro-F1 ≈ Weighted-F1: hiệu suất ổn định giữa các lớp")

    print("\n--- Ma trận nhầm lẫn (Confusion Matrix: Hàng=Thực tế, Cột=Dự đoán) ---")
    print("      " + " ".join(f"{c[:5]:>5}" for c in classes))
    for i, row in enumerate(cm):
        print(f"{classes[i][:5]:5} " + " ".join(f"{v:5d}" for v in row))

    print("\n--- Báo cáo chi tiết (Classification Report) ---")
    print(classification_report(trues, preds, labels=list(range(len(classes))),
                                target_names=classes, digits=4, zero_division=0))
    
    # Lưu kết quả chi tiết vào JSON
    results_path = os.path.join(RESULTS_DIR, "aspect_model_results.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump({
            "accuracy": acc,
            "macro_precision": macro_p,
            "macro_recall": macro_r,
            "macro_f1": macro_f1,
            "weighted_precision": p,
            "weighted_recall": r,
            "weighted_f1": f1,
            "per_class": [
                {
                    "class": classes[i],
                    "precision": cp[i],
                    "recall": cr[i],
                    "f1": cf[i],
                    "support": int(cs[i]),
                    "percentage": cs[i] / total * 100 if total > 0 else 0
                }
                for i in range(len(classes))
            ],
            "confusion_matrix": cm.tolist(),
            "class_distribution": {classes[i]: class_counts.get(classes[i], 0) for i in range(len(classes))},
            "imbalance_ratio": imbalance_ratio,
            "total_samples": total
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Kết quả đã lưu: {results_path}")


if __name__ == "__main__":
    main()