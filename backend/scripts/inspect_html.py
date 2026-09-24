# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

async def fetch(session, url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp:
        return await resp.text()

async def main():
    urls = {
        "hoangha": "https://hoanghamobile.com/dien-thoai-di-dong/apple-iphone-12-128gb-chinh-hang-vn-a",
        "clickbuy": "https://clickbuy.com.vn/apple-iphone-13-128gb-chinh-hang-vn-a.html",
    }
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for name, url in urls.items():
            html = await fetch(session, url)
            soup = BeautifulSoup(html, "html.parser")
            print(f"\n{'='*60}")
            print(f"Platform: {name}")
            
            if name == "hoangha":
                # Look inside #reviews for individual review items
                review_div = soup.select_one("#reviews")
                if review_div:
                    print("Inside #reviews:")
                    # Look for review items
                    for sel in ['.review-item', '.item-review', '.review-content', '.review-text', 'p', 'div']:
                        items = review_div.select(sel)
                        if items:
                            print(f"  {sel}: {len(items)}")
                            for item in items[:5]:
                                text = item.get_text(strip=True)
                                if 10 <= len(text) <= 500:
                                    print(f"    - {text[:150]}")
                    
                    # Print the HTML structure
                    print("\nHTML snippet of #reviews:")
                    print(str(review_div)[:2000])
                    
            elif name == "clickbuy":
                # Look for comment items inside .product-comment or .comments
                comment_div = soup.select_one(".product-comment") or soup.select_one(".comments")
                if comment_div:
                    print("Inside .product-comment/.comments:")
                    for sel in ['.comment-item', '.item', '.review-item', '.comment-content', 'p', 'div']:
                        items = comment_div.select(sel)
                        if items:
                            print(f"  {sel}: {len(items)}")
                            for item in items[:5]:
                                text = item.get_text(strip=True)
                                if 10 <= len(text) <= 500:
                                    print(f"    - {text[:150]}")
                    
                    print("\nHTML snippet:")
                    print(str(comment_div)[:2000])

if __name__ == "__main__":
    asyncio.run(main())
