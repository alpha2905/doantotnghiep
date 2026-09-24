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

for name, col_name in STORE_COLLECTIONS.items():
    col = db[col_name]
    total = col.count_documents({})
    with_url = col.count_documents({"product_url": {"$exists": True, "$ne": "", "$ne": "#"}})
    with_comments = col.count_documents({"comments": {"$exists": True, "$ne": []}})
    sample = col.find_one({"product_url": {"$exists": True, "$ne": "", "$ne": "#"}})
    print(f"{name} ({col_name}): total={total}, with_url={with_url}, with_comments={with_comments}")
    if sample:
        url = sample.get("product_url", "")
        comments = sample.get("comments", [])
        print(f"  sample url: {url}")
        print(f"  comments: {comments}")
        print(f"  comments_count: {sample.get('comments_count')}")
        print(f"  comments_updated_at: {sample.get('comments_updated_at')}")
    print()

client.close()
