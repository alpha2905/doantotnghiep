"""
Scraper & Price Updater Module for 8 E-Commerce Platforms:
- FPT Shop
- Thế Giới Di Động (TGDD)
- CellphoneS
- Hoàng Hà Mobile
- Di Động Việt
- Viettel Store
- Clickbuy
- MobileCity

Vào từng link sản phẩm trong MongoDB, cào giá mới nhất, và cập nhật price_history
phục vụ huấn luyện & dự báo giá bằng mô hình LSTM.
"""

import os
import sys
import re
import json
import asyncio
import random
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import aiohttp
from bs4 import BeautifulSoup

# Unicode encoding fix cho Windows Console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
]

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

BLOCKED_PLATFORMS = {"FPT Shop"}

MIN_VALID_PRICE = 500000        # 500.000đ (loại bỏ phụ kiện/trả góp)
MAX_VALID_PRICE = 100000000     # 100.000.000đ


def get_headers(referer: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def clean_price_text(text: Any) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", str(text))
    if not digits:
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0


def fetch_with_curl_cffi(url: str, timeout: int = 20, max_retries: int = 2) -> Optional[str]:
    if not CURL_AVAILABLE:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            domain = url.split("/")[2] if "/" in url else ""
            headers = get_headers(referer=f"https://{domain}/")
            resp = curl_requests.get(
                url,
                headers=headers,
                impersonate="chrome",
                timeout=timeout,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                text = resp.text
                if text and len(text) > 1000:
                    return text
            elif resp.status_code == 503 and attempt < max_retries:
                time.sleep(1.5 * attempt)
        except Exception as e:
            logger.debug(f"[Scraper] curl_cffi attempt {attempt} failed for {url}: {e}")
    return None


async def fetch_page(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int = 12,
    prefer_curl: bool = False,
) -> Optional[str]:
    if prefer_curl:
        html = await asyncio.to_thread(fetch_with_curl_cffi, url, timeout)
        if html:
            return html

    try:
        domain = url.split("/")[2] if "/" in url else ""
        headers = get_headers(referer=f"https://{domain}/")
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and len(text) > 1000:
                    return text
            elif resp.status in (403, 429) and not prefer_curl:
                return await asyncio.to_thread(fetch_with_curl_cffi, url, timeout)
    except Exception as e:
        logger.debug(f"[Scraper] aiohttp fetch error for {url}: {e}")
        if not prefer_curl:
            return await asyncio.to_thread(fetch_with_curl_cffi, url, timeout)

    return None


def extract_price_robust(html: str, soup: BeautifulSoup) -> int:
    """Thuật toán trích xuất giá điện thoại chuẩn xác từ HTML 8 sàn."""
    # 1. Kiểm tra JSON-LD
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
            if isinstance(data, dict):
                offers = data.get("offers")
                if isinstance(offers, dict):
                    p = clean_price_text(offers.get("price"))
                    if MIN_VALID_PRICE <= p <= MAX_VALID_PRICE:
                        return p
                elif isinstance(offers, list) and offers:
                    p = clean_price_text(offers[0].get("price"))
                    if MIN_VALID_PRICE <= p <= MAX_VALID_PRICE:
                        return p
        except Exception:
            pass

    # 2. Meta tags
    meta_selectors = [
        'meta[property="product:price:amount"]',
        'meta[itemprop="price"]',
        'meta[name="twitter:data2"]',
    ]
    for sel in meta_selectors:
        tag = soup.select_one(sel)
        if tag:
            p = clean_price_text(tag.get("content", ""))
            if MIN_VALID_PRICE <= p <= MAX_VALID_PRICE:
                return p

    # 3. CSS Price Selectors chính chủ từng sàn
    dom_selectors = [
        ".box-price-present", ".bs-price", ".price-current", ".giaban",
        ".product__price--show", ".current-product-price", ".price-new",
        ".special-price", "p.price", "span.price", "div.price", ".product-price"
    ]
    for sel in dom_selectors:
        for tag in soup.select(sel):
            p = clean_price_text(tag.text)
            if MIN_VALID_PRICE <= p <= MAX_VALID_PRICE:
                return p

    # 4. Tìm các biến JS chứa giá (cho TGDD / FPT / CellphoneS SPA)
    js_patterns = [
        r'["\']?price_current["\']?\s*:\s*(\d{7,9})',
        r'["\']?price_present["\']?\s*:\s*(\d{7,9})',
        r'["\']?Price["\']?\s*:\s*(\d{7,9})',
        r'["\']?price["\']?\s*:\s*(\d{7,9})',
        r'["\']?sale_price["\']?\s*:\s*(\d{7,9})',
        r'["\']?final_price["\']?\s*:\s*(\d{7,9})',
    ]
    for pat in js_patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            val = int(m.group(1))
            if MIN_VALID_PRICE <= val <= MAX_VALID_PRICE:
                return val

    # 5. Regex định dạng giá VNĐ (ví dụ: 29.990.000đ)
    patterns = [
        r'(\d{1,3}(?:\.\d{3}){2,3})\s*(?:₫|đ|VND|vnđ)',
        r'(\d{1,3}(?:,\d{3}){2,3})\s*(?:₫|đ|VND|vnđ)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            p = clean_price_text(m.group(1))
            if MIN_VALID_PRICE <= p <= MAX_VALID_PRICE:
                return p

    return 0


async def scrape_platform_price(
    session: aiohttp.ClientSession,
    platform: str,
    product_url: str,
    prefer_curl: bool = False,
) -> Optional[Dict[str, Any]]:
    if not product_url or product_url == "#":
        return None

    html = await fetch_page(session, product_url, prefer_curl=prefer_curl)
    if not html or len(html) < 1000:
        return None

    # Phát hiện trang 404 / redirect trang chủ (ví dụ TGDD trang ngừng kinh doanh)
    if "Thegioididong.com - Điện thoại, Laptop" in html and len(html) < 15000:
        logger.warning(f"[Scraper] Trang không khả dụng (đã chuyển hướng trang chủ): {product_url}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    price = extract_price_robust(html, soup)

    if not price or price <= 0:
        logger.warning(f"[Scraper] No price found for {platform}: {product_url}")
        return None

    now = datetime.now(timezone.utc)
    return {
        "price": f"{price:,}₫",
        "price_number": price,
        "last_scraped_at": now,
        "source": "live_scraper",
    }


async def update_product_real_price(db_col, product: Dict[str, Any], price_data: Dict[str, Any]) -> bool:
    now = price_data.get("last_scraped_at", datetime.now(timezone.utc))
    price_history = product.get("price_history", []) or []

    today_str = now.strftime("%Y-%m-%d")

    # Kiểm tra xem hôm nay đã có bản ghi lịch sử chưa, nếu có thì cập nhật, chưa thì append
    updated_history = False
    for h in price_history:
        h_date = h.get("date") or (h.get("scraped_at").strftime("%Y-%m-%d") if hasattr(h.get("scraped_at"), "strftime") else str(h.get("scraped_at"))[:10])
        if h_date == today_str:
            h["price"] = price_data["price_number"]
            h["scraped_at"] = now
            updated_history = True
            break

    if not updated_history:
        price_history.append({
            "date": today_str,
            "price": price_data["price_number"],
            "scraped_at": now,
            "source": "live_scraper",
        })

    await db_col.update_one(
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


async def update_prices_real(db, product_limit: int = 0, concurrency: int = 15, fpt_concurrency: int = 5):
    """Cập nhật giá thực tế từ link cho tất cả sản phẩm trong DB (chạy đa luồng song song)."""
    now = datetime.now(timezone.utc)
    updated_count = 0
    failed_count = 0

    # Tăng giới hạn kết nối đồng thời trong aiohttp ClientSession
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
    async with aiohttp.ClientSession(connector=connector) as session:
        for source, collection_name in STORE_COLLECTIONS.items():
            col = db[collection_name]
            cursor = col.find({"product_url": {"$exists": True, "$ne": "", "$ne": "#"}})
            if product_limit and product_limit > 0:
                cursor = cursor.limit(product_limit)
            products = await cursor.to_list(length=product_limit if product_limit and product_limit > 0 else None)

            total_store = len(products)
            if not products:
                print(f"📦 [{source}] Không tìm thấy sản phẩm nào trong DB.", flush=True)
                continue

            prefer_curl = source in BLOCKED_PLATFORMS
            # FPT Shop (curl_cffi): fpt_concurrency (mặc định 5), các sàn khác: concurrency (mặc định 15)
            store_concurrency = fpt_concurrency if prefer_curl else concurrency
            print(f"\n🚀 [{source}] Đang chạy ĐA LUỒNG ({store_concurrency} luồng song song) cho {total_store} sản phẩm...", flush=True)

            sem = asyncio.Semaphore(store_concurrency)
            request_delay = (0.3, 0.6) if prefer_curl else (0.02, 0.08)

            store_ok = 0
            store_fail = 0
            completed_counter = 0

            async def process_item(p):
                nonlocal store_ok, store_fail, updated_count, failed_count, completed_counter
                product_name = p.get("name", "Sản phẩm")
                product_url = p.get("product_url") or p.get("link") or p.get("url") or ""

                if not product_url or product_url == "#":
                    completed_counter += 1
                    store_fail += 1
                    failed_count += 1
                    return

                async with sem:
                    price_data = await scrape_platform_price(session, source, product_url, prefer_curl=prefer_curl)
                    await asyncio.sleep(random.uniform(*request_delay))

                completed_counter += 1
                if price_data:
                    await update_product_real_price(col, p, price_data)
                    store_ok += 1
                    updated_count += 1
                    print(f"  [{completed_counter}/{total_store}] ✅ {product_name[:40]}: {price_data['price']}", flush=True)
                else:
                    store_fail += 1
                    failed_count += 1
                    print(f"  [{completed_counter}/{total_store}] ⚠️ {product_name[:40]}: Không trích xuất được giá", flush=True)

            # Chạy tất cả sản phẩm song song
            await asyncio.gather(*(process_item(p) for p in products), return_exceptions=True)

            print(f"✔️ [{source}] Hoàn thành: {store_ok} thành công, {store_fail} thất bại.\n", flush=True)

    print(f"🎉 TỔNG KẾT BÁO CÁO: Đã cập nhật thành công {updated_count} sản phẩm | Thất bại: {failed_count}", flush=True)
    return {"updated": updated_count, "failed": failed_count, "total": updated_count + failed_count}


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
    parser = argparse.ArgumentParser(description="Real price scraper for 8 e-commerce platforms to update LSTM price history")
    parser.add_argument("--limit", type=int, default=0, help="Max products per platform (0 = all)")
    parser.add_argument("--concurrency", type=int, default=15, help="Số luồng song song cho các sàn thường (mặc định 15)")
    parser.add_argument("--fpt-concurrency", type=int, default=5, help="Số luồng song song cho FPT Shop (mặc định 5)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    db = await get_db()
    print(f"🚀 Bắt đầu quét và cập nhật giá thực tế cho các sản phẩm trong DB...")
    result = await update_prices_real(db, product_limit=args.limit, concurrency=args.concurrency, fpt_concurrency=args.fpt_concurrency)
    print(f"✅ Hoàn thành! Kết quả: {result}")


if __name__ == "__main__":
    asyncio.run(main())
