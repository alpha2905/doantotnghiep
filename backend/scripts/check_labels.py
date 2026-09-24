# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from pymongo import MongoClient

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"
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

# Check if any doc has extra fields besides comments
sample = db['fpt'].find_one({"comments": {"$exists": True, "$ne": []}})
if sample:
    print("Sample FPT doc keys:", list(sample.keys()))
    print("Comments field type:", type(sample.get('comments')))
    print("First comment:", sample.get('comments', [None])[0] if sample.get('comments') else None)

# Check if any collection has sentiment/aspect labels
for name, col_name in STORE_COLLECTIONS.items():
    sample = db[col_name].find_one()
    if sample:
        extra_keys = [k for k in sample.keys() if k not in ['_id', 'comments', 'comments_count', 'comments_updated_at', 'product_url', 'name', 'price', 'image_url', 'last_scraped_at', 'source', 'price_number', 'rating', 'rating_updated_at', 'price_history', 'created_at', 'updated_at']]
        if extra_keys:
            print(f"{name} ({col_name}) extra keys: {extra_keys}")

client.close()
