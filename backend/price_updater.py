import os
import re
import random
import argparse
import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

import scrapers

logger = logging.getLogger(__name__)

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


def parse_price(price):
    if not price:
        return 0
    digits = re.sub(r"[^\d]", "", str(price))
    if not digits:
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0


def vary_price(current_price: int) -> int:
    if current_price <= 0:
        return current_price
    change_pct = random.uniform(-0.03, 0.03)
    new_price = int(current_price * (1 + change_pct))
    return max(new_price, 1000)


async def get_db():
    client = AsyncIOMotorClient(MONGO_URI)
    return client[MONGO_DB]


async def update_prices_simulated(db, dry_run: bool = False):
    now = datetime.now(timezone.utc)
    updated_count = 0

    for source, collection_name in STORE_COLLECTIONS.items():
        col = db[collection_name]
        cursor = col.find({})
        products = await cursor.to_list(length=1000)

        for p in products:
            current_price = parse_price(p.get("price", "")) or p.get("price_number", 0)
            if current_price <= 0:
                continue

            new_price = vary_price(current_price)
            price_history = p.get("price_history", []) or []

            price_history.append({
                "date": now.strftime("%Y-%m-%d"),
                "price": new_price,
                "scraped_at": now,
                "source": "hourly_scheduler"
            })

            if not dry_run:
                await col.update_one(
                    {"_id": p["_id"]},
                    {
                        "$set": {
                            "price": f"{new_price:,}₫",
                            "price_number": new_price,
                            "last_scraped_at": now,
                            "price_history": price_history,
                        }
                    }
                )
            updated_count += 1

    logger.info(f"[PriceUpdater] {'[DRY RUN] ' if dry_run else ''}Simulated update: {updated_count} products at {now.isoformat()}")
    return updated_count


async def update_prices_once(dry_run: bool = False, use_real: bool = True, real_limit: int = 200):
    db = await get_db()
    now = datetime.now(timezone.utc)

    if use_real:
        try:
            logger.info("[PriceUpdater] Attempting real price scrape...")
            result = await scrapers.update_prices_real(db, product_limit=real_limit)
            if result and result.get("updated", 0) > 0:
                logger.info(f"[PriceUpdater] Real scrape succeeded: {result}")
                return result["updated"]
            else:
                logger.warning("[PriceUpdater] Real scrape returned 0 updates, falling back to simulation")
        except Exception as e:
            logger.error(f"[PriceUpdater] Real scrape failed: {e}, falling back to simulation")

    return await update_prices_simulated(db, dry_run=dry_run)


async def price_updater_loop(interval_hours: int = 1, dry_run: bool = False, use_real: bool = True):
    logger.info(f"[PriceUpdater] Starting. Interval: {interval_hours}h, dry_run: {dry_run}, use_real: {use_real}")
    while True:
        try:
            await update_prices_once(dry_run=dry_run, use_real=use_real)
        except Exception as e:
            logger.error(f"[PriceUpdater] Error: {e}")
        await asyncio.sleep(interval_hours * 60 * 60)


def main():
    parser = argparse.ArgumentParser(description="Hourly price updater for LSTM training data")
    parser.add_argument("--interval", "-i", type=int, default=1, help="Update interval in hours (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to DB")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--mongo", default=None, help="MongoDB URI override")
    parser.add_argument("--db", default=None, help="Database name override")
    parser.add_argument("--no-real", action="store_true", help="Disable real scraping, use simulation only")
    parser.add_argument("--real-limit", type=int, default=200, help="Max products per platform for real scraping")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if args.mongo:
        os.environ["MONGO_URI"] = args.mongo
    if args.db:
        os.environ["MONGO_DB"] = args.db

    use_real = not args.no_real

    if args.once:
        count = asyncio.run(update_prices_once(dry_run=args.dry_run, use_real=use_real, real_limit=args.real_limit))
        print(f"Done. Updated {count} products.")
    else:
        asyncio.run(price_updater_loop(interval_hours=args.interval, dry_run=args.dry_run, use_real=use_real))


if __name__ == "__main__":
    main()
