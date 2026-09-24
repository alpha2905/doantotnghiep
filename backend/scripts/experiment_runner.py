# -*- coding: utf-8 -*-
"""
Experiment Runner - Chạy thống nhất tất cả thí nghiệm đánh giá mô hình.
Tạo báo cáo tổng hợp cho Chương 4 đồ án.
"""
import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from typing import Dict, List, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, os.pardir))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


EXPERIMENTS = {
    "phobert_sentiment": {
        "script": "evaluate_phobert_hybrid.py",
        "description": "Đánh giá PhoBERT Sentiment: Rule-based vs PhoBERT vs Hybrid",
        "output": "phobert_sentiment_results.json"
    },
    "lstm_temporal": {
        "script": "evaluate_lstm_temporal.py",
        "description": "Đánh giá LSTM với temporal split và baseline comparison",
        "output": "lstm_temporal_results.json"
    },
    "aspect_model": {
        "script": "evaluate_aspect_model.py",
        "description": "Đánh giá Aspect Classification với xử lý mất cân bằng",
        "output": "aspect_model_results.json"
    },
    "entity_resolution": {
        "script": "evaluate_entity_resolution.py",
        "description": "Đánh giá Entity Resolution với ground truth",
        "output": "entity_resolution_results.json"
    },
    "pqs_rqs": {
        "script": "evaluate_pqs_rqs_recommendation.py",
        "description": "Đánh giá PQS/RQS và Recommendation Engine",
        "output": "pqs_rqs_results.json"
    }
}


def run_experiment(name: str, config: Dict) -> Dict:
    """Chạy một thí nghiệm và trả về kết quả."""
    script_path = os.path.join(SCRIPT_DIR, config["script"])
    if not os.path.exists(script_path):
        return {
            "name": name,
            "status": "SKIPPED",
            "error": f"Script not found: {script_path}",
            "timestamp": datetime.now().isoformat()
        }
    
    print(f"\n{'='*80}")
    print(f"🔬 CHẠY THÍ NGHIỆM: {config['description']}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5 phút timeout
            cwd=SCRIPT_DIR
        )
        
        output_file = os.path.join(RESULTS_DIR, config["output"])
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                experiment_results = json.load(f)
        else:
            experiment_results = {"stdout": result.stdout, "stderr": result.stderr}
        
        return {
            "name": name,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "return_code": result.returncode,
            "results": experiment_results,
            "timestamp": datetime.now().isoformat()
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "status": "TIMEOUT",
            "error": "Experiment timed out after 5 minutes",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "name": name,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def generate_summary_report(all_results: List[Dict]) -> str:
    """Tạo báo cáo tổng hợp markdown."""
    report = []
    report.append("# Báo cáo tổng hợp thí nghiệm\n")
    report.append(f"Thời gian chạy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("\n## Tổng kết\n")
    report.append("| Thí nghiệm | Trạng thái | Chi tiết |")
    report.append("|-----------|-----------|----------|")
    
    for res in all_results:
        status = res.get('status', 'UNKNOWN')
        detail = res.get('error', res.get('results', {}).get('summary', 'N/A'))
        report.append(f"| {res['name']} | {status} | {detail} |")
    
    report.append("\n## Chi tiết từng thí nghiệm\n")
    for res in all_results:
        report.append(f"### {res['name']}\n")
        report.append(f"- **Trạng thái**: {res.get('status', 'UNKNOWN')}")
        report.append(f"- **Thời gian**: {res.get('timestamp', 'N/A')}")
        if 'error' in res:
            report.append(f"- **Lỗi**: {res['error']}")
        if 'results' in res:
            results = res['results']
            if isinstance(results, dict):
                for key, value in results.items():
                    if key not in ['stdout', 'stderr']:
                        report.append(f"- **{key}**: {value}")
        report.append("\n")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Experiment Runner cho đồ án")
    parser.add_argument("--experiment", type=str, choices=list(EXPERIMENTS.keys()), help="Chạy thí nghiệm cụ thể")
    parser.add_argument("--all", action="store_true", help="Chạy tất cả thí nghiệm")
    parser.add_argument("--report", action="store_true", help="Tạo báo cáo tổng hợp")
    args = parser.parse_args()
    
    if not args.all and not args.experiment:
        parser.print_help()
        return
    
    results = []
    
    if args.all:
        for name, config in EXPERIMENTS.items():
            res = run_experiment(name, config)
            results.append(res)
    elif args.experiment:
        config = EXPERIMENTS[args.experiment]
        res = run_experiment(args.experiment, config)
        results.append(res)
    
    # Lưu kết quả
    summary_file = os.path.join(RESULTS_DIR, "experiment_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Tạo báo cáo markdown
    if args.report or args.all:
        report = generate_summary_report(results)
        report_file = os.path.join(RESULTS_DIR, "experiment_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 Báo cáo đã lưu: {report_file}")
    
    # In tóm tắt
    print(f"\n{'='*80}")
    print("TỔNG KẾT THÍ NGHIỆM")
    print(f"{'='*80}")
    for res in results:
        status = res.get('status', 'UNKNOWN')
        icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'
        print(f"  {icon} {res['name']}: {status}")
    
    print(f"\n💾 Kết quả chi tiết: {summary_file}")


if __name__ == "__main__":
    main()
