# -*- coding: utf-8 -*-
"""
API Load Test - Kiểm tra hiệu năng API thực với concurrent users.
Đo latency (Avg, P50, P95, P99), throughput và error rate.
"""
import os
import sys
import time
import json
import asyncio
import argparse
import statistics
from datetime import datetime
from typing import Dict, List, Tuple

import aiohttp

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Cấu hình API
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
# Endpoint thật của backend/main.py (đã kiểm chứng):
# - /api/search?name=...   : read-heavy  (regex trên 8 collection MongoDB)
# - /api/suggest?name=...  : autocomplete nhẹ (regex + dedup, giới hạn limit)
# - /api/compare?name=...  : compute-heavy (PhoBERT sentiment + LSTM + PQS/RQS,
#                             có cache TTL 10 phút -> request đầu "cold", sau đó "warm")
API_ENDPOINTS = [
    "/api/search?name=iphone",
    "/api/suggest?name=ip",
    "/api/compare?name=iphone+15",
]
# Timeout riêng: /api/compare lần đầu chạy PhoBERT+LSTM trên CPU có thể >10s
ENDPOINT_TIMEOUTS = {
    "/api/compare": 120,
}
DEFAULT_TIMEOUT = 30
WARMUP_REQUESTS = 1  # số request warm-up mỗi endpoint trước khi đo


async def make_request(session: aiohttp.ClientSession, url: str, timeout: int = 10) -> Tuple[float, int, str]:
    """Thực hiện một request và trả về (latency_ms, status_code, error)."""
    start = time.time()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            latency = (time.time() - start) * 1000
            body = await resp.text()
            if resp.status != 200:
                return latency, resp.status, f"HTTP {resp.status}: {body[:120]}"
            return latency, resp.status, ""
    except Exception as e:
        latency = (time.time() - start) * 1000
        return latency, 0, f"{type(e).__name__}: {e}"[:200]


def timeout_for_endpoint(endpoint: str) -> int:
    for prefix, t in ENDPOINT_TIMEOUTS.items():
        if prefix in endpoint:
            return t
    return DEFAULT_TIMEOUT


async def warmup(session: aiohttp.ClientSession, endpoints: List[str], base_url: str = API_BASE_URL):
    """Warm-up: cache /api/compare + JIT/torch threads trước khi đo (không tính vào kết quả)."""
    for ep in endpoints:
        for _ in range(WARMUP_REQUESTS):
            try:
                await make_request(session, f"{base_url}{ep}", timeout=timeout_for_endpoint(ep))
            except Exception:
                pass


async def worker(worker_id: int, requests_per_worker: int, endpoints: List[str], session: aiohttp.ClientSession, base_url: str = API_BASE_URL) -> List[Dict]:
    """Worker thực hiện requests."""
    results = []
    for i in range(requests_per_worker):
        endpoint = endpoints[i % len(endpoints)]
        url = f"{base_url}{endpoint}"
        latency, status, error = await make_request(session, url, timeout=timeout_for_endpoint(endpoint))
        results.append({
            "worker_id": worker_id,
            "request_id": i,
            "endpoint": endpoint,
            "latency_ms": latency,
            "status_code": status,
            "error": error
        })
    return results


async def run_load_test(num_workers: int, requests_per_worker: int, endpoints: List[str], base_url: str = API_BASE_URL) -> Dict:
    """Chạy load test với concurrent workers."""
    print(f"\n🚀 Bắt đầu load test: {num_workers} workers, {requests_per_worker} requests/worker")
    print(f"   Tổng requests: {num_workers * requests_per_worker}")
    print(f"   Endpoints: {endpoints}")
    
    connector = aiohttp.TCPConnector(limit=num_workers * 2, limit_per_host=num_workers)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Warm-up trước khi đo (không tính vào kết quả)
        await warmup(session, endpoints, base_url=base_url)

        tasks = []
        for w in range(num_workers):
            task = worker(w, requests_per_worker, endpoints, session, base_url=base_url)
            tasks.append(task)
        
        start_time = time.time()
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
    
    # Gộp kết quả
    all_results = []
    for res in worker_results:
        if isinstance(res, Exception):
            print(f"❌ Worker error: {res}")
            continue
        all_results.extend(res)
    
    return {
        "total_requests": len(all_results),
        "total_time_seconds": total_time,
        "requests_per_second": len(all_results) / total_time if total_time > 0 else 0,
        "results": all_results
    }


def analyze_results(results: List[Dict]) -> Dict:
    """Phân tích kết quả load test."""
    ok_lat = [r["latency_ms"] for r in results if r["status_code"] == 200]
    bad = [r for r in results if r["status_code"] != 200]
    
    latencies = [x for x in ok_lat]
    errors = [x for x in bad]

    if not latencies:
        err_types: Dict[str, int] = {}
        for r in results:
            key = str(r.get("error") or f"HTTP {r.get('status_code')}")
            err_types[key[:80]] = err_types.get(key[:80], 0) + 1
        return {"error": "No successful requests", "error_breakdown": err_types,
                "total_requests": len(results), "failed_requests": len(results),
                "error_rate_percent": 100.0 if results else 0.0}
    
    # Latency percentiles
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    
    def percentile(data, p):
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]
    per_endpoint: Dict[str, Dict] = {}
    for rr in results:
        bkt = per_endpoint.setdefault(rr["endpoint"], {"n": 0, "lat": [], "errors": 0})
        if rr["status_code"] == 200:
            bkt["n"] += 1
            bkt["lat"].append(rr["latency_ms"])
        else:
            bkt["errors"] += 1
    for bkt in per_endpoint.values():
        if bkt["lat"]:
            _s = sorted(bkt["lat"])
            bkt.update({"avg_ms": round(statistics.mean(_s), 1),
                        "p50_ms": round(percentile(_s, 50), 1),
                        "p95_ms": round(percentile(_s, 95), 1)})
        else:
            bkt.update({"avg_ms": 0, "p50_ms": 0, "p95_ms": 0})
        del bkt["lat"]

    
    return {
        "total_requests": len(results),
        "successful_requests": len(latencies),
        "failed_requests": len(errors),
        "error_rate_percent": len(errors) / len(results) * 100 if results else 0,
        "latency": {
            "avg_ms": statistics.mean(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "p50_ms": percentile(latencies_sorted, 50),
            "p95_ms": percentile(latencies_sorted, 95),
            "p99_ms": percentile(latencies_sorted, 99),
        },
        # Throughput đo theo wall-clock của toàn bộ đợt test:
        # throughput_rps cần total_time_seconds truyền từ run_load_test (xem main/benchmark).
        # Giữ trường này để tương thích ngược (ước lượng theo max latency).
        "throughput_rps": len(results) / (max(r["latency_ms"] for r in results) / 1000) if results else 0,
        "per_endpoint": per_endpoint,
    }


def print_report(analysis: Dict):
    """In báo cáo load test."""
    print("\n" + "=" * 80)
    print("KẾT QUẢ LOAD TEST")
    print("=" * 80)
    print(f"• Tổng requests: {analysis.get('total_requests', 0)}")
    print(f"• Thành công: {analysis.get('successful_requests', 0)}")
    print(f"• Thất bại: {analysis.get('failed_requests', 0)}")
    print(f"• Error rate: {analysis.get('error_rate_percent', 0):.2f}%")
    
    if "latency" in analysis:
        lat = analysis["latency"]
        print(f"\n• Latency (ms):")
        print(f"  - Avg: {lat['avg_ms']:.2f}")
        print(f"  - Min: {lat['min_ms']:.2f}")
        print(f"  - Max: {lat['max_ms']:.2f}")
        print(f"  - P50: {lat['p50_ms']:.2f}")
        print(f"  - P95: {lat['p95_ms']:.2f}")
        print(f"  - P99: {lat['p99_ms']:.2f}")
    
    print(f"\n• Throughput: {analysis.get('throughput_rps', 0):.2f} requests/second")

    if "per_endpoint" in analysis:
        print("\n• Theo endpoint:")
        for ep, b in analysis["per_endpoint"].items():
            print(f"  - {ep}: n={b['n']} err={b['errors']} "
                  f"avg={b['avg_ms']}ms p50={b['p50_ms']}ms p95={b['p95_ms']}ms")
    if "error_breakdown" in analysis:
        print("\n• Chi tiết lỗi:")
        for k, v in analysis["error_breakdown"].items():
            print(f"  - {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="API Load Test")
    parser.add_argument("--url", type=str, default=API_BASE_URL, help="API base URL")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 10, 25, 50], help="Số concurrent workers")
    parser.add_argument("--requests", type=int, default=10, help="Requests mỗi worker")
    parser.add_argument("--endpoints", type=str, nargs="+", default=API_ENDPOINTS, help="API endpoints")
    args = parser.parse_args()
    
    base_url = args.url
    all_analysis = {}
    
    for num_workers in args.workers:
        print(f"\n{'='*80}")
        print(f"🔬 TEST VỚI {num_workers} CONCURRENT USERS")
        print(f"{'='*80}")
        
        results = asyncio.run(run_load_test(num_workers, args.requests, args.endpoints, base_url=base_url))
        analysis = analyze_results(results["results"])
        analysis["total_time_seconds"] = results["total_time_seconds"]
        analysis["requests_per_second"] = results["requests_per_second"]
        
        print_report(analysis)
        all_analysis[f"{num_workers}_workers"] = analysis
    
    # Lưu kết quả
    output_path = os.path.join(RESULTS_DIR, "api_load_test_results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "api_base_url": base_url,
            "endpoints_tested": args.endpoints,
            "results": all_analysis
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Kết quả đã lưu: {output_path}")


if __name__ == "__main__":
    main()
