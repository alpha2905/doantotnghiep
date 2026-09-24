# -*- coding: utf-8 -*-
"""
Comment Scraper cho 8 sàn thương mại điện tử.
"""
import os
import sys
import re
import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pymongo import MongoClient
from bs4 import BeautifulSoup
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
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
]

async def fetch_page(session, url, timeout=15):
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and len(text) > 500:
                    return text
    except Exception as e:
        logger.debug(f"Fetch error: {e}")
    return None