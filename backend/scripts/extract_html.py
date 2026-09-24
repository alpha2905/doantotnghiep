import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp
from bs4 import BeautifulSoup
from pymongo import UpdateOne

try:
    from curl_cffi import requests as curl_requests
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    curl_requests = None

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scrapers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

if not CURL_AVAILABLE:
    logger.warning("[HTML] curl_cffi is NOT installed. FPT Shop and Hoàng Hà Mobile may fail.")
    logger.warning("[HTML] Install with: pip install curl-cffi")

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

MAX_CONCURRENT = int(os.environ.get("HTML_EXTRACT_CONCURRENCY", "3"))
FETCH_TIMEOUT = int(os.environ.get("HTML_FETCH_TIMEOUT", "25"))
BATCH_SIZE = int(os.environ.get("HTML_BATCH_SIZE", "500"))
HTML_MAX_LEN = int(os.environ.get("HTML_MAX_LEN", "200000"))


def get_product_url(product: dict) -> str:
    for key in ("product_url", "url", "link"):
        val = product.get(key)
        if val and val.strip() and val.strip() != "#":
            return val.strip()
    return ""


def truncate_html(html: str) -> str:
    if html is None:
        return ""
    if len(html) > HTML_MAX_LEN:
        return html[:HTML_MAX_LEN]
    return html


async def get_db():
    client = AsyncIOMotorClient(MONGO_URI)
    return client[MONGO_DB]


async def fetch_product_html(session: aiohttp.ClientSession, url: str, prefer_curl: bool = False) -> str | None:
    if not url:
        return None

    if prefer_curl and CURL_AVAILABLE:
        def _sync_fetch():
            headers = scrapers.get_headers(referer=f"https://{url.split('/')[2]}/")
            resp = curl_requests.get(
                url,
                headers=headers,
                impersonate="chrome",
                timeout=FETCH_TIMEOUT,
                allow_redirects=True,
            )
            if resp.status_code == 200 and resp.text and len(resp.text) > 500:
                return resp.text
            return None

        try:
            html = await asyncio.to_thread(_sync_fetch)
            if html:
                return html
        except Exception as e:
            logger.debug(f"[HTML] curl_cffi failed for {url}: {e}")

    try:
        headers = scrapers.get_headers(referer=f"https://{url.split('/')[2]}/")
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT),
            allow_redirects=True,
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and len(text) > 500:
                    return text
                logger.debug(f"[HTML] Empty/short response for {url}")
            else:
                logger.debug(f"[HTML] HTTP {resp.status} for {url}")
                return None
    except Exception as e:
        logger.debug(f"[HTML] aiohttp error for {url}: {e}")

    if CURL_AVAILABLE:
        try:
            def _fallback_curl():
                headers = scrapers.get_headers(referer=f"https://{url.split('/')[2]}/")
                resp = curl_requests.get(
                    url,
                    headers=headers,
                    impersonate="chrome",
                    timeout=FETCH_TIMEOUT,
                    allow_redirects=True,
                )
                if resp.status_code == 200 and resp.text and len(resp.text) > 500:
                    return resp.text
                return None

            html = await asyncio.to_thread(_fallback_curl)
            if html:
                return html
        except Exception as e:
            logger.debug(f"[HTML] fallback curl_cffi error for {url}: {e}")

    return None


def extract_price_from_html(html: str, platform: str) -> int:
    if not html:
        return 0
    soup = BeautifulSoup(html, "html.parser")

    if platform == "Thế Giới Di Động":
        price = scrapers.extract_price_from_tgdd(soup)
    elif platform == "FPT Shop":
        price = scrapers.extract_price_from_fpt(soup)
    elif platform == "CellphoneS":
        price = scrapers.extract_price_from_cellphones(soup)
    elif platform == "Hoàng Hà Mobile":
        price = scrapers.extract_price_from_hoangha(soup)
    elif platform == "Di Động Việt":
        price = scrapers.extract_price_from_didongviet(soup)
    elif platform == "Viettel Store":
        price = scrapers.extract_price_from_viettelstore(soup)
    elif platform == "Clickbuy":
        price = scrapers.extract_price_from_clickbuy(soup)
    elif platform == "MobileCity":
        price = scrapers.extract_price_from_mobilecity(soup)
    else:
        price = (
            scrapers.extract_price_from_json_ld(soup)
            or scrapers.extract_price_from_meta(soup)
            or scrapers.extract_price_from_text(soup)
            or scrapers.extract_price_from_plain_text(html)
        )

    return price or 0


PLATFORM_PRICE_SELECTORS = {
    "FPT Shop": [
        ".product-price",
        ".price-box .price",
        "[data-price]",
        ".tpt-product-price",
        "#product-price",
        ".price-current",
        ".current-price",
    ],
    "Thế Giới Di Động": ["#PriceGTM"],
    "CellphoneS": [
        ".product-info__price",
        ".price",
        ".product-price",
        "[data-price]",
        "#product-price",
        ".block-price .price",
    ],
    "Hoàng Hà Mobile": [
        ".product-price",
        ".price",
        ".price-box .price",
        "[data-price]",
        "#product-price",
        ".price-current",
        ".current-price",
    ],
    "Di Động Việt": [
        ".product-price",
        ".price",
        ".price-box .price",
        "[data-price]",
        "#product-price",
        ".price-current",
        ".current-price",
    ],
    "Viettel Store": [
        ".product-price",
        ".price",
        ".price-box .price",
        "[data-price]",
        "#product-price",
        ".price-current",
        ".current-price",
    ],
    "Clickbuy": [
        ".product-price",
        ".price",
        ".price-box .price",
        "[data-price]",
        "#product-price",
        ".price-current",
        ".current-price",
    ],
    "MobileCity": [
        ".product-price",
        ".price",
        ".price-box .price",
        "[data-price]",
        "#product-price",
        ".price-current",
        ".current-price",
    ],
}


def find_price_candidates(soup: BeautifulSoup, platform: str) -> list:
    candidates = []
    selectors = PLATFORM_PRICE_SELECTORS.get(platform, [])
    for sel in selectors:
        tags = soup.select(sel)
        for tag in tags:
            text = tag.get("data-price") or tag.get_text(" ", strip=True)
            price = scrapers.clean_price_text(text)
            if price and 10000 <= price <= 500000000:
                candidates.append({
                    "selector": sel,
                    "text": text,
                    "price": price,
                })
    return candidates


async def process_product(
    semaphore: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    product: dict,
    source: str,
    prefer_curl: bool,
) -> dict:
    url = get_product_url(product)
    if not url:
        return {
            "product_id": str(product.get("_id")),
            "url": "",
            "html": None,
            "price_number": 0,
            "status": "no_url",
            "platform_selectors": [],
        }

    async with semaphore:
        html = await fetch_product_html(session, url, prefer_curl=prefer_curl)
        await asyncio.sleep(0.1)

    if not html:
        return {
            "product_id": str(product.get("_id")),
            "url": url,
            "html": None,
            "price_number": 0,
            "status": "fetch_failed",
            "platform_selectors": [],
        }

    price_number = extract_price_from_html(html, platform=source)
    candidates = find_price_candidates(BeautifulSoup(html, "html.parser"), platform=source) if price_number > 0 else []
    status = "ok" if price_number > 0 else "no_price"

    return {
        "product_id": str(product.get("_id")),
        "url": url,
        "html": truncate_html(html),
        "price_number": price_number,
        "status": status,
        "platform_selectors": candidates,
    }


async def extract_all_html(dry_run: bool = False, limit_per_collection: int = 0):
    db = await get_db()
    now = datetime.now(timezone.utc)
    total_products = 0
    total_success = 0
    total_failed = 0
    failure_reasons = {}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    async with aiohttp.ClientSession() as session:
        for source, collection_name in STORE_COLLECTIONS.items():
            col = db[collection_name]
            cursor = col.find({})
            if limit_per_collection and limit_per_collection > 0:
                cursor = cursor.limit(limit_per_collection)
            products = await cursor.to_list(length=limit_per_collection if limit_per_collection > 0 else None)

            logger.info(f"[HTML] {source}: {len(products)} products to process")
            prefer_curl = source in scrapers.BLOCKED_PLATFORMS

            tasks = [
                process_product(semaphore, session, p, source, prefer_curl)
                for p in products
            ]

            results = []
            for i in range(0, len(tasks), BATCH_SIZE):
                batch = tasks[i:i + BATCH_SIZE]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)

            col_updates = []
            for r in results:
                if isinstance(r, Exception):
                    reason = f"exception: {type(r).__name__}: {r}"
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
                    logger.error(f"[HTML] Unexpected error on {source}: {r}")
                    total_failed += 1
                    continue

                total_products += 1
                if r["status"] == "ok":
                    total_success += 1
                else:
                    total_failed += 1
                    reason = r["status"]
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
                    if total_failed <= 3:
                        logger.info(
                            f"[HTML] Failed {source} product {r['product_id']}: "
                            f"status={r['status']}, url={r['url']}"
                        )

                if not dry_run and r.get("html"):
                    col_updates.append(
                        UpdateOne(
                            {"_id": r["product_id"]},
                            {
                                "$set": {
                                    "html": r["html"],
                                    "last_html_scraped_at": now,
                                    "platform_selectors": r.get("platform_selectors", []),
                                },
                                "$setOnInsert": {
                                    "html_scraped_at": now,
                                },
                            },
                        )
                    )

            if col_updates:
                for i in range(0, len(col_updates), 100):
                    batch = col_updates[i:i + 100]
                    if batch:
                        await col.bulk_write(batch, ordered=False)

            logger.info(
                f"[HTML] {source}: {total_success} ok, {total_failed} failed out of {total_products} total"
            )

    logger.info(f"[HTML] Done. Total: {total_products}, Success: {total_success}, Failed: {total_failed}")
    if failure_reasons:
        logger.info("[HTML] Failure reasons:")
        for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1]):
            logger.info(f"  {reason}: {count}")
    return {"total": total_products, "success": total_success, "failed": total_failed, "failure_reasons": failure_reasons}


def main():
    global MONGO_URI, MONGO_DB, MAX_CONCURRENT
    parser = argparse.ArgumentParser(
        description="Crawl HTML from product URLs in MongoDB and save to DB"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch HTML but do not write to DB",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max products per collection (0 = all)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=MAX_CONCURRENT,
        help=f"Max concurrent fetches (default: {MAX_CONCURRENT})",
    )
    parser.add_argument(
        "--mongo",
        default=None,
        help="MongoDB URI override",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="DB name override",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.mongo:
        MONGO_URI = args.mongo
    if args.db:
        MONGO_DB = args.db
    if args.concurrency:
        MAX_CONCURRENT = args.concurrency

    if args.once:
        result = asyncio.run(extract_all_html(dry_run=args.dry_run, limit_per_collection=args.limit))
        print(json.dumps(result, ensure_ascii=False))
    else:
        logger.info("Running once mode. Use --once flag.")


if __name__ == "__main__":
    main()
