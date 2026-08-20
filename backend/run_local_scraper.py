"""
Chạy scraper giá thật cho 8 sàn trên máy local (IP nhà mạng không bị chặn).

Cách dùng:
    python run_local_scraper.py --once          # chạy 1 lần
    python run_local_scraper.py --interval 3    # chạy mỗi 3 giờ (mặc định)
    python run_local_scraper.py --limit 200     # tối đa 200 sản phẩm/sàn
    python run_local_scraper.py --dry-run       # không ghi DB
"""
import os
import argparse
import asyncio
import logging
from datetime import datetime, timezone

import scrapers

logger = logging.getLogger(__name__)

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


async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    uri = os.environ.get(
        "MONGO_URI",
        os.environ.get(
            "MONGODB_URI",
            "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
        )
    )
    db_name = os.environ.get("MONGO_DB", "price_tracker")
    client = AsyncIOMotorClient(uri)
    return client[db_name]


async def run_once(dry_run: bool = False, limit: int = 200):
    db = await get_db()
    now = datetime.now(timezone.utc)

    logger.info(f"[LocalScraper] Bắt đầu scrape giá thật 8 sàn lúc {now.isoformat()}...")
    try:
        result = await scrapers.update_prices_real(db, product_limit=limit)
        if result and result.get("updated", 0) > 0:
            logger.info(f"[LocalScraper] Scrape thật thành công: {result}")
            return result["updated"]
        logger.warning("[LocalScraper] Scrape thật trả về 0 cập nhật, thử lại từng sàn...")
    except Exception as e:
        logger.error(f"[LocalScraper] Scrape thật lỗi: {e}")

    # Fallback: chạy từng sàn riêng lẻ để sàn nào được thì cập nhật sàn đó
    total_updated = 0
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for source, collection_name in STORE_COLLECTIONS.items():
            try:
                col = db[collection_name]
                cursor = col.find({}).limit(limit)
                products = await cursor.to_list(length=limit)
                updated = 0
                for p in products:
                    product_url = p.get("product_url") or p.get("link") or p.get("url") or ""
                    if not product_url or product_url == "#":
                        continue
                    price_data = await scrapers.scrape_platform_price(session, source, product_url)
                    if price_data:
                        if not dry_run:
                            await scrapers.update_product_real_price(col, p, price_data)
                        updated += 1
                    await asyncio.sleep(1.0)
                total_updated += updated
                logger.info(f"[LocalScraper] {source}: cập nhật {updated}/{len(products)} sản phẩm")
            except Exception as e:
                logger.error(f"[LocalScraper] Lỗi sàn {source}: {e}")

    logger.info(f"[LocalScraper] Hoàn tất. Tổng cập nhật: {total_updated}")
    return total_updated


async def loop(interval_hours: int = 3, dry_run: bool = False, limit: int = 200):
    logger.info(f"[LocalScraper] Chạy lặp mỗi {interval_hours} giờ. dry_run={dry_run}, limit={limit}")
    while True:
        try:
            await run_once(dry_run=dry_run, limit=limit)
        except Exception as e:
            logger.error(f"[LocalScraper] Lỗi: {e}")
        await asyncio.sleep(interval_hours * 60 * 60)


def main():
    parser = argparse.ArgumentParser(description="Scrape giá thật 8 sàn trên máy local")
    parser.add_argument("--once", action="store_true", help="Chạy 1 lần rồi thoát")
    parser.add_argument("--interval", "-i", type=int, default=3, help="Số giờ giữa các lần chạy (mặc định: 3)")
    parser.add_argument("--limit", type=int, default=200, help="Tối đa sản phẩm mỗi sàn (mặc định: 200)")
    parser.add_argument("--dry-run", action="store_true", help="Không ghi vào DB")
    parser.add_argument("--mongo", default=None, help="MongoDB URI override")
    parser.add_argument("--db", default=None, help="Tên database override")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.mongo:
        os.environ["MONGO_URI"] = args.mongo
    if args.db:
        os.environ["MONGO_DB"] = args.db

    if args.once:
        count = asyncio.run(run_once(dry_run=args.dry_run, limit=args.limit))
        print(f"\nHoan tat. Da cap nhat {count} san pham.")
    else:
        asyncio.run(loop(interval_hours=args.interval, dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()