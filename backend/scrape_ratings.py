# -*- coding: utf-8 -*-
"""
Rating Scraper cho 8 sàn thương mại điện tử.
Crawl số sao đánh giá từ trang sản phẩm và lưu vào trường `rating` trong MongoDB.

Đã kiểm tra cấu trúc HTML:
- TGDD: .point-average-score (e.g. "5"), JSON-LD
- Di Động Việt: text patterns like "4.9(12)", JSON-LD
- CellphoneS: "0.0 sa" pattern found, no JSON-LD
- Hoàng Hà Mobile: "51 người đã đánh giá" but no visible score in HTML
- FPT Shop: no rating data found in HTML
- Viettel Store: JSON-LD ratingValue=0 (placeholder)
- Clickbuy: "0/5" pattern found
- MobileCity: JSON-LD ratingValue="5" found
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
# Rating Extraction
# ---------------------------------------------------------------------------
def extract_rating_tgdd(html: str) -> Optional[float]:
    """Thế Giới Di Động - rating in .point-average-score or JSON-LD"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try .point-average-score - contains just the number like "5"
    el = soup.select_one('.point-average-score')
    if el:
        text = el.get_text(strip=True)
        match = re.search(r'(\d+(?:[.,]\d+)?)', text)
        if match:
            try:
                rating = float(match.group(1).replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    # Try .point-average-container which has "5/5"
    el = soup.select_one('.point-average-container')
    if el:
        text = el.get_text(strip=True)
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*/\s*5', text)
        if match:
            try:
                rating = float(match.group(1).replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    # Try JSON-LD
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try .rating-topzone
    el = soup.select_one('.rating-topzone')
    if el:
        text = el.get_text(strip=True)
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*/\s*5', text)
        if match:
            try:
                rating = float(match.group(1).replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    return None


def extract_rating_fpt(html: str) -> Optional[float]:
    """FPT Shop - rating in various star/rating elements"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Skip known non-rating content
    skip_words = ['kích thước', 'màn hình', 'inch', 'screen', 'size', 'camera', 'ram', 'rom',
                  'dung lượng', 'giảm ngay', 'đặc quyền', 'trả góp', 'tặng', 'hssv', 'giáo viên']
    
    # FPT Shop specific selectors - avoid broad [class*="star"] which matches product specs
    selectors = [
        '.rating-point', '.star-rating', '.rating-star', '.product-rating',
        '.rating-score', '.rating-value', '.star-rating-point',
        '[itemprop="ratingValue"]'
    ]
    
    for sel in selectors:
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            if any(word in text.lower() for word in skip_words):
                continue
            match = re.search(r'(\d+(?:[.,]\d+)?)', text)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try JSON-LD
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    return None


def extract_rating_didongviet(html: str) -> Optional[float]:
    """Di Động Việt - rating in text patterns like "4.9(12)" or "4.9/5", JSON-LD"""
    
    # Try JSON-LD first - most reliable
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try text patterns - avoid date patterns like "2026/5"
    text_patterns = [
        r'(\d+(?:[.,]\d+)?)\s*\(\d+\)',  # "4.9(12)" format
        r'(\d+(?:[.,]\d+)?)\s*sa',
        r'(\d+(?:[.,]\d+)?)\s*star',
    ]
    
    for pat in text_patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        for m in matches:
            # Skip dates like "2026/5" or "2026/05"
            if re.match(r'^19|20\d{2}$', m):
                continue
            try:
                rating = float(m.replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    return None


def extract_rating_cellphones(html: str) -> Optional[float]:
    """CellphoneS - check for "0.0 sa" pattern or other indicators"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for "0.0 sa" or similar patterns
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*sa',
        r'(\d+(?:[.,]\d+)?)\s*/\s*5',
        r'rating[:\s]*(\d+(?:[.,]\d+)?)',
        r'(\d+(?:[.,]\d+)?)\s*star',
    ]
    
    for pat in patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        for m in matches:
            try:
                rating = float(m.replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    # Try JSON-LD
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try specific selectors
    selectors = [
        '.rating', '.star', '.score', '.rate', '.points',
        '[class*="rating"]', '[class*="star"]', '[itemprop="ratingValue"]'
    ]
    
    for sel in selectors:
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            match = re.search(r'(\d+(?:[.,]\d+)?)', text)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    return None


def extract_rating_hoangha(html: str) -> Optional[float]:
    """Hoàng Hà Mobile - check for rating in HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # First try JSON-LD with validation
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Look for actual rating display - avoid filter options like "5 sao", "4 sao"
    # These are typically in dropdown/filter elements, not the main rating display
    # Look for patterns in specific contexts
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*/\s*5',  # "4.5/5" format
        r'rating[:\s]*(\d+(?:[.,]\d+)?)',  # "rating: 4.5"
    ]
    
    for pat in patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        for m in matches:
            try:
                rating = float(m.replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    # Try specific selectors - but avoid elements that are just filter lists or progress labels
    selectors = [
        '.rating', '.star', '.score', '.rate', '.points',
        '[class*="rating"]', '[class*="star"]', '[itemprop="ratingValue"]'
    ]
    
    for sel in selectors:
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            # Skip filter lists like "5 sao 4 sao 3 sao 2 sao 1 sao"
            if re.search(r'[5][\s,]*4[\s,]*3[\s,]*2[\s,]*1', text):
                continue
            # Skip progress star labels (just numbers 1-5)
            if el.get('class') and 'progress-star-label' in el.get('class'):
                continue
            # Skip elements that are just "51 người đã đánh giá" without score
            if 'người đã đánh giá' in text.lower() and not re.search(r'\d+[.,]\d+\s*/\s*5', text):
                continue
            match = re.search(r'(\d+(?:[.,]\d+)?)', text)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    return None


def extract_rating_clickbuy(html: str) -> Optional[float]:
    """Clickbuy - check for .rating-star input.rank value first, then fallback to regex"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try specific Clickbuy selectors first
    selectors = [
        '.rating-star input.rank',
        '.rating-star input[type="hidden"]',
        'input.rank',
    ]
    
    for sel in selectors:
        elements = soup.select(sel)
        for el in elements:
            val = el.get('value')
            if val is not None:
                try:
                    rating = float(val)
                    if 0 <= rating <= 5:
                        return rating
                except (ValueError, TypeError):
                    continue
    
    # Fallback to regex patterns
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*/\s*5',
        r'(\d+(?:[.,]\d+)?)\s*sa',
        r'rating[:\s]*(\d+(?:[.,]\d+)?)',
        r'(\d+(?:[.,]\d+)?)\s*star',
    ]
    
    for pat in patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        for m in matches:
            try:
                rating = float(m.replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    # Try JSON-LD
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try other selectors
    for sel in ['.rating', '.star', '.score', '.rate', '.points', '[class*="rating"]', '[class*="star"]', '[itemprop="ratingValue"]']:
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            match = re.search(r'(\d+(?:[.,]\d+)?)', text)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    return None


def extract_rating_generic(html: str) -> Optional[float]:
    """Generic extractor for other platforms"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try JSON-LD first
    json_lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in json_lds:
        if 'rating' in j.lower():
            # Skip placeholder data (ratingCount=0 or bestRating=0)
            if 'ratingCount' in j and re.search(r'"ratingCount":\s*0', j):
                continue
            if 'bestRating' in j and re.search(r'"bestRating":\s*0', j):
                continue
            match = re.search(r'"ratingValue":\s*"?(\d+(?:[.,]\d+)?)"?', j)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try common selectors
    selectors = [
        '.rating', '.star', '.score', '.rate', '.points',
        '[class*="rating"]', '[class*="star"]', '[itemprop="ratingValue"]'
    ]
    
    for sel in selectors:
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            # Skip filter lists like "5 stars4 stars3 stars2 stars1 star" or "5 sao 4 sao..."
            if re.search(r'5.*4.*3.*2.*1', text) or re.search(r'[5][\s,]*4[\s,]*3[\s,]*2[\s,]*1', text):
                continue
            match = re.search(r'(\d+(?:[.,]\d+)?)', text)
            if match:
                try:
                    rating = float(match.group(1).replace(',', '.'))
                    if 0 <= rating <= 5:
                        return rating
                except:
                    pass
    
    # Try regex patterns
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*/\s*5',
        r'rating[:\s]*(\d+(?:[.,]\d+)?)',
    ]
    
    for pat in patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        for m in matches:
            try:
                rating = float(m.replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    # Skip filter options like "5 sao 4 sao 3 sao 2 sao 1 sao" or "5 stars 4 stars..."
    filter_patterns = [
        r'(\d+(?:[.,]\d+)?)\s*sa',
        r'(\d+(?:[.,]\d+)?)\s*star',
    ]
    
    for pat in filter_patterns:
        matches = re.findall(pat, html, re.IGNORECASE)
        # Check if this looks like a filter list (multiple consecutive ratings)
        if len(matches) >= 3:
            # Check if matches contain consecutive integers like 5,4,3,2,1
            try:
                nums = [float(m.replace(',', '.')) for m in matches[:5]]
                if all(0 <= n <= 5 for n in nums) and sorted(nums, reverse=True) == nums:
                    continue  # Skip filter list
            except:
                pass
        for m in matches:
            try:
                rating = float(m.replace(',', '.'))
                if 0 <= rating <= 5:
                    return rating
            except:
                pass
    
    return None


# Map platform -> extractor function
EXTRACTORS = {
    "Thế Giới Di Động": extract_rating_tgdd,
    "FPT Shop": extract_rating_fpt,
    "Di Động Việt": extract_rating_didongviet,
    "CellphoneS": extract_rating_cellphones,
    "Hoàng Hà Mobile": extract_rating_hoangha,
    "Viettel Store": extract_rating_generic,
    "Clickbuy": extract_rating_clickbuy,
    "MobileCity": extract_rating_generic,
}


# ---------------------------------------------------------------------------
# MongoDB Operations
# ---------------------------------------------------------------------------
def get_products_with_url(db, collection_name: str, limit: int = 0) -> List[Dict]:
    """Lấy sản phẩm có product_url từ collection."""
    col = db[collection_name]
    cursor = col.find({})
    products = []
    for doc in cursor:
        url = doc.get("product_url", "")
        if url and url not in ["", "#"]:
            products.append(doc)
            if limit and len(products) >= limit:
                break
    return products


async def scrape_ratings_for_platform(
    session: aiohttp.ClientSession,
    platform_name: str,
    collection_name: str,
    limit: int = 0,
    delay_range: tuple = (0.5, 1.5),
):
    """Crawl ratings cho một sàn."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    col = db[collection_name]
    
    products = get_products_with_url(db, collection_name, limit=limit)
    if not products:
        print(f"  ⚠️ [{platform_name}] Không tìm thấy sản phẩm có product_url.")
        client.close()
        return {"platform": platform_name, "scraped": 0, "failed": 0, "total_ratings": 0}
    
    extractor = EXTRACTORS.get(platform_name, extract_rating_generic)
    scraped = 0
    failed = 0
    total_ratings = 0
    
    print(f"\n🚀 [{platform_name}] Bắt đầu crawl ratings cho {len(products)} sản phẩm...")
    
    for idx, product in enumerate(products, 1):
        product_url = product.get("product_url", "")
        if not product_url or product_url == "#":
            failed += 1
            continue
        
        if not product_url.startswith("http"):
            product_url = "https://" + product_url
        
        html = await fetch_page(session, product_url)
        if not html:
            failed += 1
            logger.info(f"  [{platform_name}] [{idx}/{len(products)}] ⚠️ Không lấy được HTML: {product.get('name', '')[:40]}")
            continue
        
        rating = extractor(html)
        
        if rating is not None:
            col.update_one(
                {"_id": product["_id"]},
                {"$set": {"rating": rating, "rating_updated_at": datetime.now(timezone.utc)}}
            )
            total_ratings += rating
            scraped += 1
            logger.info(f"  [{platform_name}] [{idx}/{len(products)}] ✅ {product.get('name', '')[:40]}: rating={rating}")
        else:
            failed += 1
            logger.debug(f"  [{platform_name}] [{idx}/{len(products)}] ⚠️ Không tìm thấy rating: {product.get('name', '')[:40]}")
        
        await asyncio.sleep(random.uniform(*delay_range))
    
    avg_rating = total_ratings / scraped if scraped > 0 else 0
    print(f"✔️ [{platform_name}] Hoàn thành: {scraped} thành công, {failed} thất bại. Rating TB: {avg_rating:.2f}")
    client.close()
    return {
        "platform": platform_name,
        "scraped": scraped,
        "failed": failed,
        "avg_rating": round(avg_rating, 2),
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Rating scraper for 8 e-commerce platforms")
    parser.add_argument("--limit", type=int, default=0, help="Số sản phẩm tối đa mỗi sàn (0 = all)")
    parser.add_argument("--concurrency", type=int, default=3, help="Số sàn chạy song song (mặc định 3)")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay cơ bản giữa request (giây)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("CRAWL RATING/SAO ĐÁNH GIÁ CHO 8 SÀN THƯƠNG MẠI ĐIỆN TỬ")
    print("=" * 80)
    
    connector = aiohttp.TCPConnector(limit=args.concurrency * 5, limit_per_host=args.concurrency, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for platform_name, collection_name in STORE_COLLECTIONS.items():
            delay_range = (args.delay, args.delay * 1.5)
            task = scrape_ratings_for_platform(
                session, platform_name, collection_name,
                limit=args.limit, delay_range=delay_range
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Tổng kết
    print("\n" + "=" * 80)
    print("TỔNG KẾT CRAWL RATINGS")
    print("=" * 80)
    total_scraped = 0
    total_failed = 0
    for res in results:
        if isinstance(res, Exception):
            print(f"  ❌ Lỗi: {res}")
            continue
        total_scraped += res["scraped"]
        total_failed += res["failed"]
        print(f"  {res['platform']}: {res['scraped']} thành công, {res['failed']} thất bại, rating TB={res['avg_rating']}")
    
    print(f"\n🎉 Tổng kết: {total_scraped} sản phẩm có rating mới | {total_failed} thất bại")


if __name__ == "__main__":
    asyncio.run(main())
