import os
import re
import json
import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import aiohttp
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    curl_requests = None

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

USER_AGENT = random.choice(USER_AGENTS)


def get_headers(referer: str = None) -> Dict[str, str]:
    """Build realistic browser headers to avoid 403 blocks."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    if referer:
        headers["Referer"] = referer
    return headers

PLATFORM_DOMAINS = {
    "FPT Shop": "fptshop.com.vn",
    "Thế Giới Di Động": "thegioididong.com",
    "CellphoneS": "cellphones.com.vn",
    "Hoàng Hà Mobile": "hoanghamobile.com",
    "Di Động Việt": "didongviet.vn",
    "Viettel Store": "viettelstore.vn",
    "Clickbuy": "clickbuy.com.vn",
    "MobileCity": "mobilecity.vn",
}


def clean_price_text(text: str) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0


def fetch_with_curl_cffi(url: str, timeout: int = 20) -> Optional[str]:
    """Fetch a page using curl_cffi with Chrome TLS impersonation.

    This bypasses TLS fingerprinting blocks (e.g. FPT Shop blocking aiohttp/python requests).
    """
    if not CURL_AVAILABLE:
        logger.warning("[Scraper] curl_cffi not installed, skipping TLS impersonation fetch")
        return None

    try:
        headers = get_headers(referer=f"https://{url.split('/')[2]}/")
        resp = curl_requests.get(
            url,
            headers=headers,
            impersonate="chrome",
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            text = resp.text
            if text and len(text) > 500:
                logger.info(f"[Scraper] curl_cffi (Chrome impersonation) fetch succeeded for {url}")
                return text
            logger.warning(f"[Scraper] curl_cffi returned empty/short content for {url}")
        else:
            logger.warning(f"[Scraper] curl_cffi HTTP {resp.status_code} for {url}")
    except Exception as e:
        logger.error(f"[Scraper] curl_cffi fetch error for {url}: {e}")

    return None


async def fetch_page(session: aiohttp.ClientSession, url: str, timeout: int = 15, max_retries: int = 3) -> Optional[str]:
    """Fetch a page with realistic browser headers.

    Strategy (optimized for local runs):
      1) aiohttp direct (1 attempt, fast)
      2) curl_cffi with Chrome TLS impersonation (bypasses TLS fingerprint blocks)
      3) r.jina.ai free reader proxy (bypasses IP blocks)
    """
    # 1) Direct attempt (single, fast)
    try:
        headers = get_headers(referer=f"https://{url.split('/')[2]}/")
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as resp:
            if resp.status == 200:
                return await resp.text()
            elif resp.status in (403, 429):
                logger.warning(f"[Scraper] HTTP {resp.status} for {url}, trying curl_cffi...")
            else:
                logger.warning(f"[Scraper] HTTP {resp.status} for {url}")
                return None
    except Exception as e:
        logger.error(f"[Scraper] Fetch error for {url}: {e}")

    # 2) Try curl_cffi with Chrome TLS impersonation (bypasses TLS fingerprint blocks)
    logger.warning(f"[Scraper] Direct fetch failed for {url}, trying curl_cffi (Chrome impersonation)...")
    html = await asyncio.to_thread(fetch_with_curl_cffi, url, timeout)
    if html:
        return html

    # 3) Fallback: fetch via r.jina.ai free reader proxy (bypasses IP blocks)
    logger.warning(f"[Scraper] curl_cffi failed for {url}, trying r.jina.ai proxy...")
    proxy_url = f"https://r.jina.ai/{url}"
    try:
        proxy_headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "X-Return-Format": "html",
        }
        async with session.get(
            proxy_url,
            headers=proxy_headers,
            timeout=aiohttp.ClientTimeout(total=timeout + 10),
            allow_redirects=True,
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and len(text) > 500:
                    logger.info(f"[Scraper] Proxy fetch succeeded for {url}")
                    return text
                logger.warning(f"[Scraper] Proxy returned empty/short content for {url}")
            else:
                logger.warning(f"[Scraper] Proxy HTTP {resp.status} for {url}")
    except Exception as e:
        logger.error(f"[Scraper] Proxy fetch error for {url}: {e}")

    logger.error(f"[Scraper] Failed to fetch {url} after all attempts")
    return None


def extract_price_from_json_ld(soup: BeautifulSoup) -> Optional[int]:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, dict):
                offers = data.get("offers")
                if isinstance(offers, dict):
                    price = offers.get("price")
                    if price:
                        return clean_price_text(str(price))
                elif isinstance(offers, list) and offers:
                    price = offers[0].get("price")
                    if price:
                        return clean_price_text(str(price))
        except Exception:
            continue
    return None


def extract_price_from_meta(soup: BeautifulSoup) -> Optional[int]:
    selectors = [
        'meta[itemprop="price"]',
        'meta[property="product:price:amount"]',
        'meta[name="twitter:data2"]',
    ]
    for sel in selectors:
        tag = soup.select_one(sel)
        if tag:
            content = tag.get("content", "")
            price = clean_price_text(content)
            if price:
                return price
    return None


def extract_price_from_text(soup: BeautifulSoup) -> Optional[int]:
    candidates = []
    for el in soup.find_all(text=re.compile(r"\d{3,}")):  # 3+ digits
        parent = el.parent
        if parent:
            text = el.strip()
            if re.search(r"₫|VND|đồng|giá|price", parent.get_text(" ", strip=True), re.IGNORECASE):
                candidates.append(text)

    for text in candidates:
        price = clean_price_text(text)
        if 10000 <= price <= 500000000:  # reasonable price range for electronics
            return price
    return None


def extract_price_from_plain_text(raw_text: str) -> Optional[int]:
    """Extract price from plain text / markdown (e.g. r.jina.ai proxy output)."""
    if not raw_text:
        return None

    # Look for price patterns like "12.990.000₫", "12,990,000 VND", "12.990.000 đ"
    patterns = [
        r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:₫|đ|VND|vnđ|đồng)",
        r"(?:₫|đ|VND|vnđ|đồng)\s*(\d{1,3}(?:[.,]\d{3})+)",
        r"(\d{1,3}(?:[.,]\d{3})+)\s*₫",
    ]
    for pat in patterns:
        for m in re.finditer(pat, raw_text, re.IGNORECASE):
            price = clean_price_text(m.group(1))
            if 10000 <= price <= 500000000:
                return price

    # Fallback: any large number near "giá" / "price"
    for m in re.finditer(r"(?:giá|price|Giá bán|Giá):?\s*(\d{1,3}(?:[.,]\d{3})+)", raw_text, re.IGNORECASE):
        price = clean_price_text(m.group(1))
        if 10000 <= price <= 500000000:
            return price

    return None


async def scrape_platform_price(session: aiohttp.ClientSession, platform: str, product_url: str) -> Optional[Dict[str, Any]]:
    domain = PLATFORM_DOMAINS.get(platform)
    if not domain or not product_url or product_url == "#":
        return None

    html = await fetch_page(session, product_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    price = (
        extract_price_from_json_ld(soup)
        or extract_price_from_meta(soup)
        or extract_price_from_text(soup)
        or extract_price_from_plain_text(html)
    )

    if not price:
        logger.warning(f"[Scraper] No price found for {platform}: {product_url}")
        return None

    now = datetime.now(timezone.utc)
    return {
        "price": f"{price:,}₫",
        "price_number": price,
        "last_scraped_at": now,
        "source": "live_scraper",
    }


async def update_product_real_price(db, product: Dict[str, Any], price_data: Dict[str, Any]) -> bool:
    now = price_data.get("last_scraped_at", datetime.now(timezone.utc))
    price_history = product.get("price_history", []) or []

    price_history.append({
        "date": now.strftime("%Y-%m-%d"),
        "price": price_data["price_number"],
        "scraped_at": now,
        "source": "live_scraper",
    })

    await db.update_one(
        {"_id": product["_id"]},
        {
            "$set": {
                "price": price_data["price"],
                "price_number": price_data["price_number"],
                "last_scraped_at": now,
                "price_history": price_history,
            }
        }
    )
    return True


async def update_prices_real(db, product_limit: int = 0):
    """Update real prices for all products (or up to product_limit if > 0).

    product_limit <= 0 means ALL products in the collection.
    """
    now = datetime.now(timezone.utc)
    updated_count = 0
    failed_count = 0

    async with aiohttp.ClientSession() as session:
        for source, collection_name in STORE_COLLECTIONS.items():
            col = db[collection_name]
            cursor = col.find({})
            if product_limit and product_limit > 0:
                cursor = cursor.limit(product_limit)
            products = await cursor.to_list(length=product_limit if product_limit and product_limit > 0 else None)

            for p in products:
                product_url = p.get("product_url") or p.get("link") or p.get("url") or ""
                if not product_url or product_url == "#":
                    failed_count += 1
                    continue

                price_data = await scrape_platform_price(session, source, product_url)
                if price_data:
                    await update_product_real_price(col, p, price_data)
                    updated_count += 1
                else:
                    failed_count += 1

                # Random delay between requests to avoid rate limiting / 403 blocks
                await asyncio.sleep(random.uniform(1.0, 3.0))

    logger.info(
        f"[Scraper] Done at {now.isoformat()}. "
        f"Updated: {updated_count}, Failed: {failed_count}"
    )
    return {"updated": updated_count, "failed": failed_count, "total": updated_count + failed_count}


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


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Real price scraper for e-commerce platforms")
    parser.add_argument("--limit", type=int, default=0, help="Max products per platform (0 = all)")
    parser.add_argument("--mongo", default=None, help="MongoDB URI override")
    parser.add_argument("--db", default=None, help="DB name override")
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

    db = await get_db()
    result = await update_prices_real(db, product_limit=args.limit)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
