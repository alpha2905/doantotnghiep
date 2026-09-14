# -*- coding: utf-8 -*-
"""
Script Benchmark API Load Test (Đánh giá hiệu năng FastAPI Backend):
- Đo THẬT qua HTTP với các mức concurrent users (mặc định 1, 10, 25, 50)
- Đo đạc Latency (Average, P50, P95, P99), Throughput (req/sec) và Error Rate (%)
- Breakdown theo từng endpoint (/api/search, /api/suggest, /api/compare)
"""

import sys
import time
import asyncio
import argparse
import json
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Hàm mô phỏng cũ đã loại bỏ (Requirement 14: đo thật qua HTTP).
# Giữ stub để tương thích ngược nếu code khác còn import.
def simulate_api_request(concurrent_users):
    raise RuntimeError("simulate_api_request đã bị loại bỏ: dùng load_test.run_load_test để đo thật.")

def benchmark_load():
    print(f"\n==========================================================================")
    print(f"THỰC NGHIỆM API LOAD TEST BENCHMARK (FASTAPI BACKEND & MONGODB ATLAS)")
    print(f"==========================================================================")
    print("Đo thật qua HTTP (không mô phỏng): latency Avg/P50/P95/P99, throughput, error rate.\n")

    parser = argparse.ArgumentParser(description="API Load Test Benchmark (real HTTP)")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 10, 25, 50],
                        help="Các mức concurrent users")
    parser.add_argument("--requests", type=int, default=10, help="Requests mỗi worker")
    parser.add_argument("--url", type=str, default=None, help="API base URL override")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from load_test import run_load_test, analyze_results, print_report, API_BASE_URL, API_ENDPOINTS

    base_url = args.url or API_BASE_URL
    concurrent_levels = args.workers
    requests_per_level = args.requests
    all_results = {}

    for users in concurrent_levels:
        print(f"\n{'='*80}")
        print(f"TEST VỚI {users} CONCURRENT USERS")
        print(f"{'='*80}")

        try:
            results = asyncio.run(run_load_test(users, requests_per_level, API_ENDPOINTS, base_url=base_url))
            analysis = analyze_results(results["results"])
            analysis["total_time_seconds"] = results["total_time_seconds"]
            analysis["requests_per_second"] = results["requests_per_second"]
            print_report(analysis)
            all_results[f"{users}_workers"] = analysis
        except Exception as e:
            print(f"Lỗi khi test với {users} users: {e}")
            all_results[f"{users}_workers"] = {"error": str(e)}

    # Lưu kết quả
    output_path = os.path.join(os.path.dirname(__file__), "model", "results", "api_benchmark_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "api_base_url": base_url,
            "endpoints_tested": API_ENDPOINTS,
            "concurrent_levels": concurrent_levels,
            "requests_per_level": requests_per_level,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nKết quả đã lưu: {output_path}")
    
    # Bảng tổng hợp
    print("\n" + "=" * 80)
    print("BẢNG TỔNG HỢP KẾT QUẢ API LOAD TEST")
    print("=" * 80)
    print(f"{'Users':>6} | {'Avg Latency':>12} | {'P95 Latency':>12} | {'P99 Latency':>12} | {'Throughput':>12} | {'Error Rate':>10}")
    print("-" * 80)
    for users in concurrent_levels:
        key = f"{users}_workers"
        if key in all_results and "latency" in all_results[key]:
            r = all_results[key]
            lat = r["latency"]
            print(f"{users:>6} | {lat['avg_ms']:>10.1f} ms | {lat['p95_ms']:>10.1f} ms | {lat['p99_ms']:>10.1f} ms | {r['requests_per_second']:>10.1f} r/s | {r['error_rate_percent']:>8.2f}%")
        else:
            print(f"{users:>6} | {'ERROR':>12} | {'ERROR':>12} | {'ERROR':>12} | {'ERROR':>12} | {'ERROR':>10}")

if __name__ == "__main__":
    benchmark_load()
