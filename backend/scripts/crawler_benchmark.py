"""
Crawler Benchmark - Đánh giá hiệu năng crawler theo từng nguồn (source).

Metrics cho luận văn:
- Source coverage  : số sản phẩm / % có URL, giá, comments, rating, HTML trong DB
- Success rate     : tỷ lệ fetch thành công trên mẫu URL thử nghiệm (live)
- Latency          : thời gian phản hồi (avg, p50, p95) theo từng nguồn
- Errors           : phân loại lỗi (timeout, DNS, HTTP 403/404/5xx, empty, parse)

Usage:
  python backend/crawler_benchmark.py --db-only              # chỉ phân tích coverage từ DB
  python backend/crawler_benchmark.py --sample 5             # + live fetch 5 URL/nguồn
  python backend/crawler_benchmark.py --sample 5 --limit 20  # giới hạn tổng SP đọc từ DB
"""
import asyncio
import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

import aiohttp
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from curl_cffi import requests as curl_requests
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    curl_requests = None

import scrapers

MONGO_URI = os.environ.get(
    "MONGO_URI",
    os.environ.get(
        "MONGODB_URI",
        "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
    ),
)
MONGO_DB = os.environ.get("MONGO_DB", "price_tracker")

# Giống STORE_COLLECTIONS trong extract_html.py
SOURCES = {
    "FPT Shop": "fpt",
    "Thế Giới Di Động": "tgdd",
    "CellphoneS": "cellphones",
    "Hoàng Hà Mobile": "hoangha",
    "Di Động Việt": "didongviet",
    "Viettel Store": "viettelstore",
    "Clickbuy": "clickbuy",
    "MobileCity": "mobilecity",
}

FETCH_TIMEOUT = int(os.environ.get("HTML_FETCH_TIMEOUT", "25"))
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "results")


def get_product_url(p: dict) -> str:
    for key in ("product_url", "url", "link"):
        val = p.get(key)
        if val and str(val).strip() and str(val).strip() != "#":
            return str(val).strip()
    return ""


def classify_error(exc: Exception) -> str:
    """Phân loại lỗi fetch phục vụ báo cáo."""
    msg = str(exc).lower()
    if isinstance(exc, asyncio.TimeoutError) or "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "ssl" in msg:
        return "ssl_error"
    if "blocked" in msg or "captcha" in msg or "403" in msg:
        return "blocked_or_403"
    if any(f"{code}" in msg for code in (404, 410)):
        return "http_404"
    if any(f"{code}" in msg for code in (500, 502, 503, 504)):
        return "http_5xx"
    return "network_or_other"


def fetch_sync(url: str) -> tuple:
    """Fetch 1 URL bằng curl_cffi (giả Chrome). Trả về (status, html, latency_ms)."""
    headers = scrapers.get_headers(referer=f"https://{url.split('/')[2]}/")
    t0 = time.perf_counter()
    resp = curl_requests.get(
        url, headers=headers, impersonate="chrome",
        timeout=FETCH_TIMEOUT, allow_redirects=True,
    )
    lat = (time.perf_counter() - t0) * 1000
    if resp.status_code == 200 and resp.text and len(resp.text) > 500:
        return resp.status_code, resp.text, lat
    return resp.status_code, resp.text or "", lat


def percentile(values: list, p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
    return s[k]
def analyze_db_coverage(col, limit: int = 0) -> dict:
    """Coverage theo DB: tổng SP, % URL, % giá, % comments, % rating, % HTML."""
    projection = {
        "product_url": 1, "url": 1, "link": 1, "price_number": 1,
        "comments": 1, "comments_count": 1, "rating": 1, "html": 1,
    }
    cursor = col.find({}, projection)
    total = 0
    with_url = with_price = with_comments = with_rating = with_html = 0
    price_values = []
    for p in cursor:
        total += 1
        if get_product_url(p):
            with_url += 1
        price = int(p.get("price_number") or 0)
        if price > 0:
            with_price += 1
            price_values.append(price)
        comments = p.get("comments")
        n_comments = p.get("comments_count") or (len(comments) if isinstance(comments, list) else 0)
        if n_comments and n_comments > 0:
            with_comments += 1
        if p.get("rating"):
            with_rating += 1
        if p.get("html"):
            with_html += 1
        if limit and total >= limit:
            break

    def pct(n: int) -> float:
        return round(n / total * 100, 2) if total else 0.0

    return {
        "total_products": total,
        "url_coverage_pct": pct(with_url),
        "price_coverage_pct": pct(with_price),
        "comments_coverage_pct": pct(with_comments),
        "rating_coverage_pct": pct(with_rating),
        "html_coverage_pct": pct(with_html),
        "min_price": min(price_values) if price_values else 0,
        "max_price": max(price_values) if price_values else 0,
    }


async def live_fetch_sample(products: list, sample_size: int, concurrency: int = 3) -> dict:
    """Fetch mẫu URL thật để đo success rate + latency + lỗi."""
    urls = [get_product_url(p) for p in products]
    urls = [u if u.startswith("http") else "https://" + u for u in urls if u]
    urls = urls[:sample_size]
    if not urls:
        return {"sample_size": 0, "success": 0, "failed": 0,
                "success_rate_pct": 0.0,
                "latency_ms": {"avg": 0, "p50": 0, "p95": 0}, "errors": {}}

    sem = asyncio.Semaphore(concurrency)
    latencies, error_counter = [], {}

    async def fetch_one(session, url):
        async with sem:
            if CURL_AVAILABLE:
                try:
                    status, html, lat = await asyncio.to_thread(fetch_sync, url)
                except Exception as e:
                    reason = classify_error(e)
                    error_counter[reason] = error_counter.get(reason, 0) + 1
                    return ("error", reason, 0.0)
            else:
                try:
                    t0 = time.perf_counter()
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT),
                        allow_redirects=True,
                    ) as resp:
                        lat = (time.perf_counter() - t0) * 1000
                        if resp.status != 200:
                            reason = f"http_{resp.status}"
                            error_counter[reason] = error_counter.get(reason, 0) + 1
                            return ("error", reason, lat)
                        html = await resp.text()
                        status = resp.status
                except Exception as e:
                    reason = classify_error(e)
                    error_counter[reason] = error_counter.get(reason, 0) + 1
                    return ("error", reason, 0.0)
            if status == 200 and html and len(html) > 500:
                latencies.append(lat)
                return ("ok", None, lat)
            reason = f"empty_or_blocked_{status}"
            error_counter[reason] = error_counter.get(reason, 0) + 1
            return ("error", reason, lat)

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch_one(session, u) for u in urls])

    success = sum(1 for r in results if r[0] == "ok")
    failed = len(results) - success
    return {
        "sample_size": len(urls),
        "success": success,
        "failed": failed,
        "success_rate_pct": round(success / len(urls) * 100, 2) if urls else 0.0,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 1) if latencies else 0,
            "p50": round(percentile(latencies, 50), 1) if latencies else 0,
            "p95": round(percentile(latencies, 95), 1) if latencies else 0,
        },
        "errors": error_counter,
    }


def print_report(results: dict):
    print("=" * 110)
    print("CRAWLER BENCHMARK - ĐÁNH GIÁ THEO TỪNG NGUỒN")
    print(f"Thời điểm chạy: {results['timestamp']}")
    print("=" * 110)
    header = (f"{'Nguồn':<20}{'SP':>6}{'URL%':>7}{'Giá%':>7}{'Cmt%':>7}"
              f"{'Rate%':>7}{'Succ%':>7}{'Avg ms':>9}{'P95 ms':>9}  Lỗi")
    print(header)
    print("-" * 110)
    for name, r in results["sources"].items():
        cov = r["coverage"]
        live = r.get("live", {})
        err_str = ", ".join(f"{k}x{v}" for k, v in live.get("errors", {}).items()) or "-"
        print(
            f"{name:<20}"
            f"{cov['total_products']:>6}"
            f"{cov['url_coverage_pct']:>7.1f}"
            f"{cov['price_coverage_pct']:>7.1f}"
            f"{cov['comments_coverage_pct']:>7.1f}"
            f"{cov.get('rating_coverage_pct', 0):>7.1f}"
            f"{live.get('success_rate_pct', 0):>7.1f}"
            f"{live.get('latency_ms', {}).get('avg', 0):>9.0f}"
            f"{live.get('latency_ms', {}).get('p95', 0):>9.0f}"
            f"  {err_str}"
        )
    print("=" * 110)
    print("Lưu ý: Succ%/Avg/P95 chỉ áp dụng khi chạy với --sample > 0 (live fetch).")


async def run_benchmark(sample: int, limit: int, mongo: str | None, db: str | None):
    global MONGO_URI, MONGO_DB
    if mongo:
        MONGO_URI = mongo
    if db:
        MONGO_DB = db

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db_obj = client[MONGO_DB]

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_size": sample,
        "sources": {},
    }

    for name, col_name in SOURCES.items():
        col = db_obj[col_name]
        print(f"\n>>> Đang đánh giá nguồn: {name} (collection: {col_name})")
        cov = analyze_db_coverage(col, limit=limit)
        results["sources"][name] = {"coverage": cov, "live": {}}
        print(f"    DB: {cov['total_products']} SP, URL {cov['url_coverage_pct']}%, "
              f"giá {cov['price_coverage_pct']}%, comments {cov['comments_coverage_pct']}%")

        if sample > 0:
            products = list(col.find({}, {"product_url": 1, "url": 1, "link": 1})
                            .limit(max(limit, sample) if limit else sample * 5))
            live = await live_fetch_sample(products, sample)
            results["sources"][name]["live"] = live
            print(f"    Live: {live['success']}/{live['sample_size']} ok, "
                  f"avg {live['latency_ms']['avg']} ms, p95 {live['latency_ms']['p95']} ms")

    client.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Crawler Benchmark theo nguồn")
    parser.add_argument("--sample", type=int, default=0, help="Số URL fetch thử mỗi nguồn (0 = chỉ phân tích DB)")
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số SP đọc từ DB mỗi nguồn")
    parser.add_argument("--mongo", default=None, help="MongoDB URI override")
    parser.add_argument("--db", default=None, help="DB name override")
    parser.add_argument("--out", default=None, help="Đường dẫn file JSON output")
    args = parser.parse_args()

    results = asyncio.run(run_benchmark(args.sample, args.limit, args.mongo, args.db))

    print_report(results)

    out_path = args.out or os.path.join(
        RESULTS_DIR, f"crawler_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu kết quả: {out_path}")


if __name__ == "__main__":
    main()




