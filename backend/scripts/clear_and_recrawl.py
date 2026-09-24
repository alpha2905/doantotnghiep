# -*- coding: utf-8 -*-
"""Xóa tất cả comments cũ trong DB và crawl lại."""
import os
import sys
import asyncio
from datetime import datetime, timezone

from pymongo import MongoClient
from scrape_comments import STORE_COLLECTIONS, scrape_comments_for_platform

MONGO_URI = os.environ.get(
    "MONGO_URI",
    os.environ.get(
        "MONGODB_URI",
        "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
    )
)
MONGO_DB = os.environ.get("MONGO_DB", "price_tracker")


def clear_comments():
    """Xóa trường comments, comments_count, comments_updated_at khỏi tất cả products."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    
    total_cleared = 0
    for platform, col_name in STORE_COLLECTIONS.items():
        col = db[col_name]
        result = col.update_many(
            {"comments": {"$exists": True}},
            {"$set": {
                "comments": [],
                "comments_count": 0,
                "comments_updated_at": datetime.now(timezone.utc)
            }}
        )
        print(f"  [{platform}] Đã xóa {result.modified_count} products' comments")
        total_cleared += result.modified_count
    
    client.close()
    print(f"\n✅ Tổng cộng đã xóa comments của {total_cleared} products")


async def crawl_all(limit_per_platform: int = 0, delay: float = 1.5):
    """Crawl comments cho tất cả 8 sàn."""
    print(f"\n🚀 Bắt đầu crawl comments cho 8 sàn...")
    print(f"   Limit mỗi sàn: {limit_per_platform if limit_per_platform else 'all'}")
    print(f"   Delay: {delay}s\n")
    
    connector = None
    try:
        import aiohttp
        connector = aiohttp.TCPConnector(limit_per_host=3, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for platform_name, collection_name in STORE_COLLECTIONS.items():
                delay_range = (delay, delay * 1.8)
                task = scrape_comments_for_platform(
                    session, platform_name, collection_name,
                    limit=limit_per_platform, delay_range=delay_range
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        if connector:
            connector.close()
    
    print("\n" + "=" * 80)
    print("TỔNG KẾT CRAWL COMMENTS")
    print("=" * 80)
    total_scraped = 0
    total_comments = 0
    for res in results:
        if isinstance(res, Exception):
            print(f"  ❌ Lỗi: {res}")
            continue
        total_scraped += res.get("scraped", 0)
        total_comments += res.get("total_comments", 0)
        print(f"  {res['platform']}: +{res.get('total_comments', 0)} comments ({res.get('scraped', 0)} thành công, {res.get('failed', 0)} thất bại)")
    
    print(f"\n🎉 Tổng kết: {total_scraped} sản phẩm có comments mới | +{total_comments} comments tổng cộng")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Xóa comments cũ và crawl lại")
    parser.add_argument("--limit", type=int, default=0, help="Số sản phẩm mỗi sàn (0 = all)")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay giữa requests (giây)")
    parser.add_argument("--no-crawl", action="store_true", help="Chỉ xóa, không crawl lại")
    args = parser.parse_args()
    
    print("=" * 80)
    print("XÓA COMMENTS CŨ VÀ CRAWL LẠI")
    print("=" * 80)
    
    # Bước 1: Xóa comments cũ
    print("\n📋 Bước 1: Xóa comments cũ...")
    clear_comments()
    
    # Bước 2: Crawl lại
    if not args.no_crawl:
        print("\n📋 Bước 2: Crawl comments mới...")
        asyncio.run(crawl_all(limit_per_platform=args.limit, delay=args.delay))
    else:
        print("\n⏭ Bỏ qua crawl (--no-crawl)")
