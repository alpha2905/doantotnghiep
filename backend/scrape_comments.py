# -*- coding: utf-8 -*-
"""
Comment Scraper cho 8 sàn thương mại điện tử:
- FPT Shop
- Thế Giới Di Động (TGDD)
- CellphoneS
- Hoàng Hà Mobile
- Di Động Việt
- Viettel Store
- Clickbuy
- MobileCity

Đọc product_url từ MongoDB, cào bình luận từ trang sản phẩm,
lưu vào trường `comments` (mảng string) và `comments_count`, `comments_updated_at`.

Lưu ý:
- Mỗi sàn có cấu trúc HTML khác nhau, cần điều chỉnh selector khi cần.
- Chạy với giới hạn tốc độ để tránh bị chặn.
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
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from pymongo import MongoClient
from bs4 import BeautifulSoup
import aiohttp

# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTML Fetching
# ---------------------------------------------------------------------------
async def fetch_page(session: aiohttp.ClientSession, url: str, timeout: int = 15) -> Optional[str]:
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and len(text) > 500:
                    return text
            else:
                logger.debug(f"HTTP {resp.status} for {url}")
    except Exception as e:
        logger.debug(f"Fetch error for {url}: {e}")
    return None

# ---------------------------------------------------------------------------
# Comment Extraction - Platform Specific
# ---------------------------------------------------------------------------

def extract_comments_tgdd(html: str) -> List[str]:
    """Thế Giới Di Động - comments thường nằm trong .comment-list hoặc div chứa 'Bình luận'"""
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    
    # Selectors phổ biến cho TGDD
    selectors = [
        ".comment-list .comment-content",
        ".comment-list .content",
        ".comment-item .comment-text",
        ".comment-item .content",
        "[class*='comment'] [class*='content']",
        "[class*='comment'] p",
        ".review-content",
        ".review-text",
    ]
    
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if text and len(text) > 5:
                comments.append(text)
    
    # Fallback: tìm đoạn văn bản có vẻ là comment
    if not comments:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if 20 <= len(text) <= 500 and any(kw in text.lower() for kw in ["máy", "dùng", "tốt", "xấu", "pin", "mua", "hài lòng", "thất vọng"]):
                comments.append(text)
    
    return comments[:20]  # Giới hạn 20 comment mỗi sản phẩm


def extract_comments_fpt(html: str) -> List[str]:
    """FPT Shop - comments trong .review-list, .comment-list"""
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    
    selectors = [
        ".review-list .review-content",
        ".review-list .content",
        ".comment-list .comment-text",
        ".comment-item .content",
        "[class*='review'] [class*='content']",
        "[class*='comment'] [class*='text']",
    ]
    
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if text and len(text) > 5:
                comments.append(text)
    
    if not comments:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if 20 <= len(text) <= 500 and any(kw in text.lower() for kw in ["máy", "dùng", "tốt", "xấu", "pin", "mua"]):
                comments.append(text)
    
    return comments[:20]


def extract_comments_cellphones(html: str) -> List[str]:
    """CellphoneS"""
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    
    selectors = [
        ".comment-list .comment-content",
        ".comment-list .content",
        ".review-item .review-text",
        "[class*='comment'] [class*='content']",
        "[class*='review'] p",
    ]
    
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if text and len(text) > 5:
                comments.append(text)
    
    if not comments:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if 20 <= len(text) <= 500 and any(kw in text.lower() for kw in ["máy", "dùng", "tốt", "xấu", "pin"]):
                comments.append(text)
    
    return comments[:20]


def extract_comments_hoangha(html: str) -> List[str]:
    """Hoàng Hà Mobile"""
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    
    selectors = [
        ".comment-list .comment-content",
        ".comment-list .content",
        ".review-content",
        "[class*='comment'] [class*='content']",
        "[class*='review'] p",
    ]
    
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if text and len(text) > 5:
                comments.append(text)
    
    if not comments:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if 20 <= len(text) <= 500 and any(kw in text.lower() for kw in ["máy", "dùng", "tốt", "xấu", "pin"]):
                comments.append(text)
    
    return comments[:20]


def extract_comments_generic(html: str) -> List[str]:
    """Generic extractor cho các sàn còn lại"""
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    
    # Thử các selector chung
    selectors = [
        ".comment-list .content",
        ".comment-list p",
        ".review-list .content",
        ".review-list p",
        "[class*='comment'] p",
        "[class*='review'] p",
        "[class*='comment'] [class*='text']",
    ]
    
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if text and 10 <= len(text) <= 500:
                comments.append(text)
    
    # Fallback: regex tìm đoạn văn bản có vẻ là comment
    if not comments:
        patterns = [
            r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*review[^"]*"[^>]*>(.*?)</div>',
        ]
        for pat in patterns:
            matches = re.findall(pat, html, re.IGNORECASE | re.DOTALL)
            for m in matches:
                text = re.sub(r'<[^>]+>', '', m).strip()
                if 10 <= len(text) <= 500:
                    comments.append(text)
    
    return comments[:20]


# Map platform -> extractor function
EXTRACTORS = {
    "Thế Giới Di Động": extract_comments_tgdd,
    "FPT Shop": extract_comments_fpt,
    "CellphoneS": extract_comments_cellphones,
    "Hoàng Hà Mobile": extract_comments_hoangha,
    "Di Động Việt": extract_comments_generic,
    "Viettel Store": extract_comments_generic,
    "Clickbuy": extract_comments_generic,
    "MobileCity": extract_comments_generic,
}


# ---------------------------------------------------------------------------
# MongoDB Operations
# ---------------------------------------------------------------------------
def get_products_with_url(db, collection_name: str, limit: int = 50) -> List[Dict]:
    """Lấy sản phẩm có product_url từ collection."""
    col = db[collection_name]
    # Lấy tất cả và lọc trong Python để tránh vấn đề $exists với một số collection
    cursor = col.find({})
    products = []
    for doc in cursor:
        url = doc.get("product_url", "")
        if url and url not in ["", "#"]:
            products.append(doc)
            if limit and len(products) >= limit:
                break
    return products


def update_product_comments(col, product_id: Any, new_comments: List[str]):
    """Cập nhật comments cho sản phẩm."""
    now = datetime.now(timezone.utc)
    # Merge với comments cũ, tránh duplicate
    existing = col.find_one({"_id": product_id}, {"comments": 1})
    old_comments = existing.get("comments", []) if existing else []
    if isinstance(old_comments, str):
        old_comments = [old_comments]
    
    # Merge và deduplicate
    merged = list(dict.fromkeys([str(c).strip() for c in old_comments if str(c).strip()] + new_comments))
    
    col.update_one(
        {"_id": product_id},
        {
            "$set": {
                "comments": merged,
                "comments_count": len(merged),
                "comments_updated_at": now,
            }
        }
    )


# ---------------------------------------------------------------------------
# Main Scraper
# ---------------------------------------------------------------------------
async def scrape_comments_for_platform(
    session: aiohttp.ClientSession,
    platform_name: str,
    collection_name: str,
    limit: int = 30,
    delay_range: tuple = (1.0, 2.5),
):
    """Crawl comments cho một sàn."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    col = db[collection_name]
    
    # Di Động Việt: cần headless browser, tạm bỏ qua
    if platform_name == "Di Động Việt":
        print(f"\n⚠️ [{platform_name}] Tạm bỏ qua: site dùng Next.js SSR, comments load bằng JS.")
        client.close()
        return {"platform": platform_name, "scraped": 0, "failed": 0, "total_comments": 0}
    
    products = get_products_with_url(db, collection_name, limit=limit)
    if not products:
        print(f"  ⚠️ [{platform_name}] Không tìm thấy sản phẩm có product_url.")
        client.close()
        return {"platform": platform_name, "scraped": 0, "failed": 0, "total_comments": 0}
    
    # Giới hạn số sản phẩm
    if limit > 0:
        products = products[:limit]
    
    extractor = EXTRACTORS.get(platform_name, extract_comments_generic)
    scraped = 0
    failed = 0
    total_comments = 0
    
    print(f"\n🚀 [{platform_name}] Bắt đầu crawl comments cho {len(products)} sản phẩm...")
    
    for idx, product in enumerate(products, 1):
        product_url = product.get("product_url", "")
        if not product_url or product_url == "#":
            failed += 1
            continue
        
        # Đảm bảo URL có protocol
        if not product_url.startswith("http"):
            product_url = "https://" + product_url
        
        html = await fetch_page(session, product_url)
        if not html:
            failed += 1
            logger.info(f"  [{platform_name}] [{idx}/{len(products)}] ⚠️ Không lấy được HTML: {product.get('name', '')[:40]}")
            continue
        
        # Extract comments
        new_comments = extractor(html)
        
        if new_comments:
            update_product_comments(col, product["_id"], new_comments)
            total_comments += len(new_comments)
            scraped += 1
            logger.info(f"  [{platform_name}] [{idx}/{len(products)}] ✅ {product.get('name', '')[:40]}: +{len(new_comments)} comments")
        else:
            failed += 1
            logger.info(f"  [{platform_name}] [{idx}/{len(products)}] ⚠️ Không tìm thấy comments: {product.get('name', '')[:40]}")
        
        # Delay để tránh bị chặn
        await asyncio.sleep(random.uniform(*delay_range))
    
    print(f"✔️ [{platform_name}] Hoàn thành: {scraped} thành công, {failed} thất bại. Tổng +{total_comments} comments.")
    client.close()
    return {
        "platform": platform_name,
        "scraped": scraped,
        "failed": failed,
        "total_comments": total_comments,
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Comment scraper for 8 e-commerce platforms")
    parser.add_argument("--limit", type=int, default=0, help="Số sản phẩm tối đa mỗi sàn (0 = all)")
    parser.add_argument("--concurrency", type=int, default=3, help="Số sàn chạy song song (mặc định 3)")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay cơ bản giữa request (giây)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("CRAWL COMMENTS CHO 8 SÀN THƯƠNG MẠI ĐIỆN TỬ")
    print("=" * 80)
    
    connector = aiohttp.TCPConnector(limit=args.concurrency * 5, limit_per_host=args.concurrency, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for platform_name, collection_name in STORE_COLLECTIONS.items():
            delay_range = (args.delay, args.delay * 1.8)
            task = scrape_comments_for_platform(
                session, platform_name, collection_name,
                limit=args.limit, delay_range=delay_range
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Tổng kết
    print("\n" + "=" * 80)
    print("TỔNG KẾT CRAWL COMMENTS")
    print("=" * 80)
    total_scraped = 0
    total_failed = 0
    total_comments = 0
    for res in results:
        if isinstance(res, Exception):
            print(f"  ❌ Lỗi: {res}")
            continue
        total_scraped += res["scraped"]
        total_failed += res["failed"]
        total_comments += res["total_comments"]
        print(f"  {res['platform']}: +{res['total_comments']} comments ({res['scraped']} thành công, {res['failed']} thất bại)")
    
    print(f"\n🎉 Tổng kết: {total_scraped} sản phẩm có comments mới | +{total_comments} comments tổng cộng")


if __name__ == "__main__":
    asyncio.run(main())
