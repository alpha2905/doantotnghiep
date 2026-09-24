# -*- coding: utf-8 -*-
"""
Label comments from MongoDB using trained PhoBERT models with batching.
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import re
import json
import argparse
from typing import List, Dict

import torch
import torch.nn.functional as F
from pymongo import MongoClient
from transformers import AutoTokenizer, RobertaForSequenceClassification

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SENT_MODEL_DIR = os.path.join(PROJECT_ROOT, "model", "phobert_models", "sentiment_classification", "final_model")
ASPECT_MODEL_DIR = os.path.join(PROJECT_ROOT, "model", "phobert_models", "aspect_classification", "final_model")


def get_comments_from_db() -> List[Dict]:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    comments = []
    seen = set()
    for platform, col_name in STORE_COLLECTIONS.items():
        col = db[col_name]
        cursor = col.find({"comments": {"$exists": True, "$ne": []}}, {"comments": 1, "product_url": 1, "name": 1})
        for doc in cursor:
            for c in doc.get("comments", []):
                if isinstance(c, str):
                    text = c.strip()
                    text = re.sub(r'\s+', ' ', text)
                    if text and len(text) >= 3 and text not in seen:
                        seen.add(text)
                        comments.append({
                            "text": text,
                            "platform": platform,
                            "product_url": doc.get("product_url", ""),
                            "product_name": doc.get("name", ""),
                        })
    client.close()
    return comments


def load_label_mapping(model_dir: str) -> Dict[int, str]:
    # label_mapping.json is stored alongside the final_model folder
    parent = os.path.dirname(model_dir)
    for candidate in [model_dir, parent]:
        path = os.path.join(candidate, "label_mapping.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            return {int(v): k for k, v in mapping.items()}
    return None


@torch.no_grad()
def predict_batch(texts: List[str], tokenizer, model, device, max_length=128, batch_size=32) -> List[int]:
    preds = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(
            batch,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        outputs = model(**inputs)
        batch_preds = torch.argmax(outputs.logits, dim=-1).cpu().tolist()
        preds.extend(batch_preds)
    return preds


def main():
    parser = argparse.ArgumentParser(description="Label DB comments with PhoBERT")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Device: {device}")

    print("📂 Loading models...")
    tokenizer = AutoTokenizer.from_pretrained(SENT_MODEL_DIR, use_fast=False, local_files_only=True)
    sent_model = RobertaForSequenceClassification.from_pretrained(
        SENT_MODEL_DIR, num_labels=3, local_files_only=True
    )
    aspect_model = RobertaForSequenceClassification.from_pretrained(
        ASPECT_MODEL_DIR, num_labels=10, local_files_only=True
    )
    sent_model.to(device).eval()
    aspect_model.to(device).eval()

    sent_label_map = load_label_mapping(SENT_MODEL_DIR)
    aspect_label_map = load_label_mapping(ASPECT_MODEL_DIR)
    print(f"   Sentiment labels: {sent_label_map}")
    print(f"   Aspect labels: {aspect_label_map}")

    print("📊 Loading comments from MongoDB...")
    comments = get_comments_from_db()
    print(f"   Total unique comments: {len(comments)}")

    texts = [c["text"] for c in comments]
    print("🏷️ Predicting sentiment...")
    sent_preds = predict_batch(texts, tokenizer, sent_model, device, batch_size=args.batch_size)
    print("🏷️ Predicting aspect...")
    aspect_preds = predict_batch(texts, tokenizer, aspect_model, device, batch_size=args.batch_size)

    results = []
    for item, sent_id, aspect_id in zip(comments, sent_preds, aspect_preds):
        sent_label = sent_label_map.get(sent_id, str(sent_id)) if sent_label_map else str(sent_id)
        aspect_label = aspect_label_map.get(aspect_id, str(aspect_id)) if aspect_label_map else str(aspect_id)
        results.append({
            "text": item["text"],
            "sentiment": sent_label,
            "aspect": aspect_label,
            "platform": item["platform"],
            "product_url": item["product_url"],
            "product_name": item["product_name"],
        })

    out_path = args.output
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for obj in results:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"✅ Saved {len(results)} labeled comments to {out_path}")


if __name__ == "__main__":
    main()
