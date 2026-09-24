# -*- coding: utf-8 -*-
"""
Debug scraper: run one product through the full pipeline and log each step.
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import random
from pymongo import MongoClient
from bs4 import BeautifulSoup
import aiohttp

MONGO_URI = "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
MONGO_DB = "price_tracker"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

async def fetch_page(session, url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status == 200:
            text = await resp.text()
            if text and len(text) > 500:
                return text
        return None

def extract_comments_tgdd(html):
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    for tag in soup.select(".comment-list li .cmt-content .cmt-txt"):
        text = tag.get_text(strip=True)
        if text and 5 <= len(text) <= 1000:
            comments.append(text)
    for tag in soup.select(".comment-list li .support"):
        text = tag.get_text(strip=True)
        if text and 5 <= len(text) <= 1000:
            comments.append(text)
    if not comments:
        for sel in [".comment-list .content", ".review-list .content", "[class*='comment'] [class*='text']"]:
            for tag in soup.select(sel):
                text = tag.get_text(strip=True)
                if text and 10 <= len(text) <= 1000:
                    comments.append(text)
    return comments[:20]

def extract_comments_fpt(html):
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    comment_rows = soup.select(".flex.flex-col .flex.gap-2")
    if not comment_rows:
        comment_rows = soup.select("[class*='flex'][class*='flex-col'] [class*='flex'][class*='gap-2']")
    for row in comment_rows:
        text_div = row.select_one(".text-textOnWhitePrimary.b2-regular .break-word")
        if not text_div:
            text_div = row.select_one("[class*='b2-regular'] [class*='break-word']")
        if not text_div:
            text_div = row.select_one("[class*='b2-medium']")
        if text_div:
            text = text_div.get_text(strip=True)
            if text and 5 <= len(text) <= 1000:
                comments.append(text)
    if not comments:
        for sel in [".comment-list .content", ".review-list .content", "[class*='comment'] [class*='text']"]:
            for tag in soup.select(sel):
                text = tag.get_text(strip=True)
                if text and 10 <= len(text) <= 500:
                    comments.append(text)
    return comments[:20]

def extract_comments_hoangha(html):
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    for tag in soup.select(".comment-block .comment-text"):
        text = tag.get_text(strip=True)
        if text and len(text) > 5:
            comments.append(text)
    for tag in soup.select(".comment-block .reply-box .reply-text"):
        text = tag.get_text(strip=True)
        if text and len(text) > 5:
            comments.append(text)
    if not comments:
        for sel in [".comment-list .content", ".review-list .content", "[class*='comment'] [class*='text']"]:
            for tag in soup.select(sel):
                text = tag.get_text(strip=True)
                if text and 10 <= len(text) <= 1000:
                    comments.append(text)
    return comments[:20]

def extract_comments_viettelstore(html):
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    for tag in soup.select(".cmt-item .c"):
        text = tag.get_text(strip=True)
        if text and 5 <= len(text) <= 1000:
            comments.append(text)
    if not comments:
        for sel in [".comment-list .content", ".review-list .content", "[class*='comment'] [class*='text']"]:
            for tag in soup.select(sel):
                text = tag.get_text(strip=True)
                if text and 10 <= len(text) <= 1000:
                    comments.append(text)
    return comments[:20]

def extract_comments_clickbuy(html):
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    for tag in soup.select(".comments-list .item .item-content"):
        text = tag.get_text(strip=True)
        if text and 10 <= len(text) <= 1000:
            comments.append(text)
    if not comments:
        for tag in soup.select(".review-list .content, .comment-list .content"):
            text = tag.get_text(strip=True)
            if text and 10 <= len(text) <= 500:
                comments.append(text)
    return comments[:20]

EXTRACTORS = {
    "Thế Giới Di Động": extract_comments_tgdd,
    "FPT Shop": extract_comments_fpt,
    "Hoàng Hà Mobile": extract_comments_hoangha,
    "Viettel Store": extract_comments_viettelstore,
    "Clickbuy": extract_comments_clickbuy,
}

async def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    
    tests = [
        ("FPT Shop", "fpt", "https://fptshop.com.vn/dien-thoai/benco-s1-pro"),
        ("Thế Giới Di Động", "tgdd", "https://www.thegioididong.com/dtdd/honor-400-5g-12gb-256gb-den"),
        ("Hoàng Hà Mobile", "hoangha", "https://hoanghamobile.com/dien-thoai-di-dong/apple-iphone-12-128gb-chinh-hang-vn-a"),
        ("Viettel Store", "viettelstore", "https://viettelstore.vn/dien-thoai/dien-thoai-dinh-vi-tre-em-masstel-alfa-5-pid354674.html"),
        ("Clickbuy", "clickbuy", "https://clickbuy.com.vn/apple-iphone-13-128gb-chinh-hang-vn-a.html"),
    ]
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for platform_name, col_name, url in tests:
            print(f"\n{'='*60}")
            print(f"Platform: {platform_name}")
            print(f"URL: {url}")
            
            html = await fetch_page(session, url)
            if not html:
                print("  ❌ Failed to fetch HTML")
                continue
            
            print(f"  HTML length: {len(html)}")
            
            extractor = EXTRACTORS.get(platform_name)
            if not extractor:
                print("  ⚠️ No extractor")
                continue
            
            comments = extractor(html)
            print(f"  Comments found: {len(comments)}")
            for i, c in enumerate(comments[:5]):
                print(f"    [{i}] {c[:120]}")
            
            # Also check DB state
            col = db[col_name]
            doc = col.find_one({"product_url": url})
            if doc:
                print(f"  DB comments_count: {doc.get('comments_count')}")
                print(f"  DB comments: {doc.get('comments')[:3] if doc.get('comments') else []}")
            else:
                print("  ⚠️ No matching doc in DB")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
