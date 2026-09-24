# -*- coding: utf-8 -*-
"""
Extract comments from MongoDB and prepare for PhoBERT training.
Outputs a single UTF-8 text file with one comment per line.
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import re
from pymongo import MongoClient

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

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
db = client[MONGO_DB]

comments = []
seen = set()

for platform, col_name in STORE_COLLECTIONS.items():
    col = db[col_name]
    cursor = col.find({"comments": {"$exists": True, "$ne": []}}, {"comments": 1})
    for doc in cursor:
        for c in doc.get("comments", []):
            if isinstance(c, str):
                text = c.strip()
                if text and text not in seen:
                    seen.add(text)
                    comments.append(text)

client.close()

# Clean comments
def clean_comment(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    # Remove UI fragments / likely noise heuristics (keep only if reasonably long)
    if len(text) < 3:
        return ""
    return text

cleaned = [clean_comment(c) for c in comments if clean_comment(c)]
cleaned = list(dict.fromkeys(cleaned))

out_path = os.path.join(os.path.dirname(__file__), "comments_for_phobert.txt")
with open(out_path, "w", encoding="utf-8") as f:
    for line in cleaned:
        f.write(line + "\n")

print(f"Total raw comments: {len(comments)}")
print(f"Total cleaned unique comments: {len(cleaned)}")
print(f"Saved to: {out_path}")
