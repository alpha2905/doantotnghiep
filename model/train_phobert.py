import os
import sys
import torch
import json
import pandas as pd
import numpy as np

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

import transformers.utils.import_utils as hf_import_utils
import transformers.trainer as hf_trainer
hf_import_utils.check_torch_load_is_safe = lambda: None
hf_trainer.check_torch_load_is_safe = lambda: None

# Fix lỗi UnicodeEncodeError trên Windows console (cp1252 không encode được emoji)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    TrainerCallback
)
from transformers.trainer_utils import get_last_checkpoint
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import warnings
warnings.filterwarnings('ignore')

# === CẤU HÌNH HỆ THỐNG ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MODEL_NAME = "vinai/phobert-base-v2"
MAX_LENGTH = 128
BATCH_SIZE = 16
EPOCHS = 15  
LEARNING_RATE = 2e-5
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "phobert_models")

# Đảm bảo sử dụng GPU nếu có
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

os.makedirs(OUTPUT_DIR, exist_ok=True)

class CommentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        encoding = self.tokenizer(
            text, truncation=True, padding='max_length',
            max_length=self.max_length, return_tensors='pt'
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    accuracy = accuracy_score(labels, preds)
    f1 = f1_score(labels, preds, average='weighted')
    return {'accuracy': accuracy, 'f1': f1}

class ProgressCallback(TrainerCallback):
    def on_epoch_begin(self, args, state, control, **kwargs):
        print(f"\n🚀 Bắt đầu epoch {int(state.epoch + 1)}/{EPOCHS}")

    def on_epoch_end(self, args, state, control, **kwargs):
        print(f"✅ Hoàn thành epoch {int(state.epoch)}")


def train_phobert(task_name, train_texts, train_labels, val_texts, val_labels, label_mapping):
    print(f"\n{'='*80}\n🔥 ĐANG THỰC HIỆN TASK: {task_name}\n{'='*80}")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    task_output_dir = os.path.join(OUTPUT_DIR, task_name)
    os.makedirs(task_output_dir, exist_ok=True)

    # Kiểm tra checkpoint để resume
    last_checkpoint = get_last_checkpoint(task_output_dir)
    while last_checkpoint and not os.path.exists(os.path.join(last_checkpoint, "trainer_state.json")):
        print(f"⚠️ Checkpoint bị hỏng hoặc chưa lưu xong: {last_checkpoint}. Tự động dọn dẹp...")
        import shutil
        shutil.rmtree(last_checkpoint, ignore_errors=True)
        last_checkpoint = get_last_checkpoint(task_output_dir)

    resume_from_checkpoint = last_checkpoint if last_checkpoint else None
    if last_checkpoint:
        print(f"🔄 Tìm thấy checkpoint hợp lệ: {last_checkpoint}. Sẽ resume training.")
    else:
        print("🆕 Không tìm thấy checkpoint hợp lệ. Bắt đầu huấn luyện mới.")
    
    # Load model
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(label_mapping), use_safetensors=True
    ).to(device)
    
    train_dataset = CommentDataset(train_texts, train_labels, tokenizer, MAX_LENGTH)
    val_dataset = CommentDataset(val_texts, val_labels, tokenizer, MAX_LENGTH)

    training_args = TrainingArguments(
        output_dir=task_output_dir,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_steps=500,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=3,  # Giữ 3 checkpoints tốt nhất
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        fp16=torch.cuda.is_available(),  # Sử dụng FP16 nếu có GPU
        report_to="none",
        logging_steps=100,
        save_steps=500,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[ProgressCallback(), EarlyStoppingCallback(early_stopping_patience=3)]
    )
    
    # Huấn luyện với resume nếu có
    if resume_from_checkpoint:
        print(f"🔄 Tiếp tục huấn luyện từ checkpoint: {resume_from_checkpoint}")
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    else:
        print("🆕 Bắt đầu huấn luyện mới...")
        trainer.train()
    
    # Lưu model cuối cùng
    final_path = os.path.join(task_output_dir, "final_model")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)
    
    with open(os.path.join(task_output_dir, "label_mapping.json"), "w", encoding="utf-8") as f:
        json.dump(label_mapping, f, ensure_ascii=False, indent=2)

    print(f"✅ HOÀN TẤT: Model đã được lưu tại {final_path}")

def main():
    # === SỬ DỤNG JSONL TRAINING DATA ĐÃ CÂN BẰNG ===
    # Sentiment: dữ liệu comments từ datn (MongoDB Atlas) đã weak-label + cân bằng
    sentiment_file = os.path.join(DATA_DIR, "phobert_train_sentiment_datn_balanced.jsonl")
    # Aspect: giữ dữ liệu aspect hiện có
    aspect_file = os.path.join(DATA_DIR, "phobert_train_aspect.jsonl")

    # Load dữ liệu sentiment
    if os.path.exists(sentiment_file):
        print("\n📌 CHẠY TASK 1: SENTIMENT CLASSIFICATION")
        texts, labels = [], []
        with open(sentiment_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    texts.append(data['text'])
                    labels.append(data['label'])
                except:
                    continue
        
        sentiment_mapping = {'positive': 0, 'neutral': 1, 'negative': 2}
        sentiment_encoded = [sentiment_mapping[label] for label in labels if label in sentiment_mapping]
        texts_filtered = [t for t, l in zip(texts, labels) if l in sentiment_mapping]
        
        s_train_t, s_val_t, s_train_l, s_val_l = train_test_split(
            texts_filtered, sentiment_encoded, test_size=0.2, random_state=42, stratify=sentiment_encoded
        )
        train_phobert("sentiment_classification", s_train_t, s_train_l, s_val_t, s_val_l, sentiment_mapping)
    else:
        print(f"❌ Lỗi: Không tìm thấy {sentiment_file}")

        # ==================== LOAD DỮ LIỆU ASPECT ====================
    aspect_file = os.path.join(DATA_DIR, "phobert_train_aspect.jsonl")
    if os.path.exists(aspect_file):
        print("\n📌 CHẠY TASK 2: ASPECT CLASSIFICATION")
        
        texts, labels = [], []
        with open(aspect_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    texts.append(data['text'])
                    labels.append(data['label'])
                except:
                    continue

        # === XỬ LÝ CLASS HIẾM ===
        from collections import Counter
        class_counts = Counter(labels)
        
        # Giữ lại chỉ những class có ít nhất 3 mẫu (an toàn hơn)
        min_samples = 3
        valid_labels = {lbl for lbl, cnt in class_counts.items() if cnt >= min_samples}
        
        # Lọc dữ liệu
        filtered_texts = []
        filtered_labels = []
        removed = 0
        for t, l in zip(texts, labels):
            if l in valid_labels:
                filtered_texts.append(t)
                filtered_labels.append(l)
            else:
                removed += 1

        print(f"Đã loại {removed} mẫu thuộc các lớp quá hiếm (< {min_samples} mẫu).")
        print(f"Số lớp còn lại: {len(valid_labels)}")
        print("Phân bố lớp sau khi lọc:")
        print(pd.Series(filtered_labels).value_counts().sort_values())

        # Tạo mapping mới chỉ với class hợp lệ
        unique_aspects = sorted(list(valid_labels))
        aspect_mapping = {aspect: idx for idx, aspect in enumerate(unique_aspects)}
        
        # Encode lại
        aspect_encoded = [aspect_mapping[label] for label in filtered_labels]

        # Split với stratify
        a_train_t, a_val_t, a_train_l, a_val_l = train_test_split(
            filtered_texts, aspect_encoded, 
            test_size=0.2, 
            random_state=42, 
            stratify=aspect_encoded
        )

        train_phobert("aspect_classification", a_train_t, a_train_l, a_val_t, a_val_l, aspect_mapping)
    else:
        print(f"❌ Lỗi: Không tìm thấy {aspect_file}")

if __name__ == "__main__":
    main()