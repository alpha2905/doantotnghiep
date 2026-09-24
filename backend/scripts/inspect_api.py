# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import aiohttp
import random
import re
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
        "viettelstore": "https://viettelstore.vn/dien-thoai/dien-thoai-dinh-vi-tre-em-masstel-alfa-5-pid354674.html",
        "clickbuy": "https://clickbuy.com.vn/apple-iphone-13-128gb-chinh-hang-vn-a.html",
        "hoangha": "https://hoanghamobile.com/dien-thoai-di-dong/apple-iphone-12-128gb-chinh-hang-vn-a",
    }
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for name, url in urls.items():
            html = await fetch(session, url)
            print(f"\n{'='*60}")
            print(f"Platform: {name}")
            print(f"HTML length: {len(html)}")
            
            # Search for AJAX/API endpoints
            api_patterns = [
                r'["\'](/[^"\']*comment[^"\']*)["\']',
                r'["\'](/[^"\']*review[^"\']*)["\']',
                r'["\'](/[^"\']*ajax[^"\']*)["\']',
                r'["\'](/[^"\']*api[^"\']*)["\']',
            ]
            
            print("API endpoints found:")
            for pat in api_patterns:
                matches = re.findall(pat, html, re.IGNORECASE)
                for m in matches[:10]:
                    print(f"  {m}")
            
            # Look for JavaScript that loads comments
            print("\nComment-related JS:")
            comment_js = re.findall(r'<script[^>]*>(.*?)(?:loadComment|loadReview|getComment|getReview|comment|review).*?</script>', html, re.IGNORECASE | re.DOTALL)
            for js in comment_js[:3]:
                print(f"  {js[:200]}")
            
            # Look for data attributes that might contain comment data
            print("\nData attributes with comments:")
            data_attrs = re.findall(r'data-[^=]*="[^"]*(?:comment|review)[^"]*"', html, re.IGNORECASE)
            for attr in data_attrs[:10]:
                print(f"  {attr}")

if __name__ == "__main__":
    asyncio.run(main())
