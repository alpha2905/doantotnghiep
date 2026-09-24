# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from pymongo import MongoClient

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
db = client[MONGO_DB]

for col_name in ['hoangha', 'didongviet', 'viettelstore', 'clickbuy']:
    docs = list(db[col_name].find({"product_url": {"$ne": "", "$ne": "#"}}).limit(3))
    print(f"{col_name} ({len(docs)} samples):")
    for d in docs:
        print(" ", d.get("product_url"))
    print()

client.close()
