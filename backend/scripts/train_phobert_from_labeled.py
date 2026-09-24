# -*- coding: utf-8 -*-
"""
Train PhoBERT models from existing labeled JSONL data.
"""
import os
os.environ["TRANSFORMERS_NO_TORCH_LOAD_SAFETY_CHECK"] = "1"

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import random
import argparse
from collections import defaultdict, Counter
from typing import List, Dict

import torch
import numpy as np
import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
)

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

import transformers.utils.import_utils as hf_import_utils
import transformers.trainer as hf_trainer
hf_import_utils.check_torch_load_is_safe = lambda: None
hf_trainer.check_torch_load_is_safe = lambda: None

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
PHOBERT_BASE = "vinai/phobert-base-v2"

# Default paths
DEFAULT_DATA = os.path.join(BASE_DIR, "data", "comments_labeled_from_db.jsonl")
DEFAULT_SENT_DATA = os.path.join(BASE_DIR, "data", "phobert_train_sentiment_datn_balanced.jsonl")
DEFAULT_ASPECT_DATA = os.path.join(BASE_DIR, "data", "phobert_train_aspect.jsonl")
DEFAULT_SENT_OUTPUT = os.path.join(BASE_DIR, "model", "phobert_models", "sentiment_classification", "final_model")
DEFAULT_ASPECT_OUTPUT = os.path.join(BASE_DIR, "model", "phobert_models", "aspect_classification", "final_model")


def load_jsonl(path: str):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return data


def get_dataset(texts: List[str], labels: List[int], tokenizer, max_length=128) -> Dataset:
    def tokenize_fn(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )

    ds = Dataset.from_dict({"text": texts, "label": labels})
    ds = ds.map(tokenize_fn, batched=True, remove_columns=["text"])
    return ds


def train_classifier(
    texts: List[str],
    labels: List[int],
    id2label: Dict[int, str],
    output_dir: str,
    epochs: int = 15,
    batch_size: int = 8,
    device: torch.device = None,
):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    num_labels = len(id2label)
    print(f"   Training on {len(texts)} samples, {num_labels} classes")
    print(f"   Label distribution: {dict(Counter(labels))}")
    print(f"   Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(PHOBERT_BASE, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        PHOBERT_BASE, num_labels=num_labels, ignore_mismatched_sizes=True,
        use_safetensors=True
    ).to(device)

    ds = get_dataset(texts, labels, tokenizer)
    split = ds.train_test_split(test_size=0.1, seed=42)

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")

    training_args = TrainingArguments(
        output_dir=output_dir,
        overwrite_output_dir=True,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Save label mapping
    with open(os.path.join(output_dir, "label_mapping.json"), "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in id2label.items()}, f, ensure_ascii=False)

    print(f"✅ Saved model to {output_dir}")
    return trainer


def main():
    parser = argparse.ArgumentParser(description="Train PhoBERT from labeled JSONL")
    parser.add_argument("--sentiment-data", default=DEFAULT_SENT_DATA)
    parser.add_argument("--aspect-data", default=DEFAULT_ASPECT_DATA)
    parser.add_argument("--data", default=DEFAULT_DATA, help="Single labeled JSONL with text/sentiment/aspect")
    parser.add_argument("--use-db-labeled", action="store_true", help="Use comments_labeled_from_db.jsonl as main source")
    parser.add_argument("--only-aspect", action="store_true", help="Only train aspect model, skip sentiment training")
    parser.add_argument("--output-sentiment", default=DEFAULT_SENT_OUTPUT)
    parser.add_argument("--output-aspect", default=DEFAULT_ASPECT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Device: {device}")

    if args.use_db_labeled or args.data != DEFAULT_DATA:
        source_path = args.data
        print(f"\n📚 Loading labeled data from {source_path}")
        data = load_jsonl(source_path)
        print(f"   Loaded {len(data)} samples")

        sent_texts = []
        sent_labels_str = []
        aspect_texts = []
        aspect_labels_str = []
        for d in data:
            text = d.get("text", "").strip()
            sentiment = d.get("sentiment")
            aspect = d.get("aspect")
            if not text:
                continue
            if sentiment:
                sent_texts.append(text)
                sent_labels_str.append(sentiment)
            if aspect:
                aspect_texts.append(text)
                aspect_labels_str.append(aspect)

        # -----------------------------------------------------------------------
        # Train Sentiment
        # -----------------------------------------------------------------------
        if not args.only_aspect:
            print("\n" + "=" * 60)
            print("TRAINING SENTIMENT MODEL")
            print("=" * 60)

            if sent_texts:
                sent_label2id = {v: i for i, v in enumerate(sorted(set(sent_labels_str)))}
                sent_labels = [sent_label2id[l] for l in sent_labels_str]
                sent_id2label = {v: k for k, v in sent_label2id.items()}
                print(f"   Labels: {sent_label2id}")

                train_classifier(
                    sent_texts,
                    sent_labels,
                    sent_id2label,
                    args.output_sentiment,
                    epochs=args.epochs,
                    batch_size=args.batch_size,
                    device=device,
                )
            else:
                print("❌ Không có nhãn sentiment trong file")

        # -----------------------------------------------------------------------
        # Train Aspect
        # -----------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TRAINING ASPECT MODEL")
        print("=" * 60)

        if aspect_texts:
            from collections import Counter
            class_counts = Counter(aspect_labels_str)
            min_samples = 3
            valid_labels = {lbl for lbl, cnt in class_counts.items() if cnt >= min_samples}

            filtered_texts = []
            filtered_labels = []
            removed = 0
            for t, l in zip(aspect_texts, aspect_labels_str):
                if l in valid_labels:
                    filtered_texts.append(t)
                    filtered_labels.append(l)
                else:
                    removed += 1

            print(f"Đã loại {removed} mẫu thuộc các lớp quá hiếm (< {min_samples} mẫu).")
            print(f"Số lớp còn lại: {len(valid_labels)}")
            print("Phân bố lớp sau khi lọc:")
            print(pd.Series(filtered_labels).value_counts().sort_values())

            unique_aspects = sorted(list(valid_labels))
            aspect_mapping = {aspect: idx for idx, aspect in enumerate(unique_aspects)}
            aspect_encoded = [aspect_mapping[label] for label in filtered_labels]

            train_classifier(
                filtered_texts,
                aspect_encoded,
                aspect_mapping,
                args.output_aspect,
                epochs=args.epochs,
                batch_size=args.batch_size,
                device=device,
            )
        else:
            print("❌ Không có nhãn aspect trong file")
    else:
        # -----------------------------------------------------------------------
        # Train Sentiment
        # -----------------------------------------------------------------------
        if not args.only_aspect:
            print("\n" + "=" * 60)
            print("TRAINING SENTIMENT MODEL")
            print("=" * 60)

            print(f"📚 Loading sentiment data from {args.sentiment_data}")
            sent_data = load_jsonl(args.sentiment_data)
            print(f"   Loaded {len(sent_data)} samples")

            sent_texts = [d["text"] for d in sent_data]
            sent_labels_str = [d["label"] for d in sent_data]
            sent_label2id = {v: i for i, v in enumerate(sorted(set(sent_labels_str)))}
            sent_labels = [sent_label2id[l] for l in sent_labels_str]
            sent_id2label = {v: k for k, v in sent_label2id.items()}

            print(f"   Labels: {sent_label2id}")

            train_classifier(
                sent_texts,
                sent_labels,
                sent_id2label,
                args.output_sentiment,
                epochs=args.epochs,
                batch_size=args.batch_size,
                device=device,
            )

        # -----------------------------------------------------------------------
        # Train Aspect
        # -----------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("TRAINING ASPECT MODEL")
        print("=" * 60)

        print(f"📚 Loading aspect data from {args.aspect_data}")
        aspect_data = load_jsonl(args.aspect_data)
        print(f"   Loaded {len(aspect_data)} samples")

        aspect_texts = [d["text"] for d in aspect_data]
        aspect_labels_str = [d["label"] for d in aspect_data]
        aspect_label2id = {v: i for i, v in enumerate(sorted(set(aspect_labels_str)))}
        aspect_labels = [aspect_label2id[l] for l in aspect_labels_str]
        aspect_id2label = {v: k for k, v in aspect_label2id.items()}

        print(f"   Labels: {aspect_label2id}")

        train_classifier(
            aspect_texts,
            aspect_labels,
            aspect_id2label,
            args.output_aspect,
            epochs=args.epochs,
            batch_size=args.batch_size,
            device=device,
        )

    print("\n🎉 Training complete!")


if __name__ == "__main__":
    main()
