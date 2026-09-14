# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pymongo import MongoClient

c = MongoClient('mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham')
db = c['price_tracker']
cols = {
    'FPT Shop': 'fpt',
    'Thế Giới Di Động': 'tgdd',
    'CellphoneS': 'cellphones',
    'Hoàng Hà Mobile': 'hoangha',
    'Di Động Việt': 'didongviet',
    'Viettel Store': 'viettelstore',
    'Clickbuy': 'clickbuy',
    'MobileCity': 'mobilecity',
}
for k, v in cols.items():
    total = db[v].count_documents({})
    with_url = db[v].count_documents({'product_url': {'$nin': ['', None, '#']}})
    print(f'{k}: {total} total, {with_url} with url')
c.close()
