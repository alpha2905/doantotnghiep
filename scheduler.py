# scheduler.py
"""
Tự động crawl dữ liệu giá từ các sàn TMĐT theo lịch trình
Chạy lệnh: python scheduler.py
"""

import os
import sys
import subprocess
import schedule
import time
from datetime import datetime
from threading import Thread
import logging

# === CẤU HÌNH ===
CRAWL_INTERVAL_HOURS = 6  # Crawl mỗi 6 giờ
CRAWL_TIME = "02:00"       # Crawl lúc 2h sáng hàng ngày

# Danh sách các script crawl
CRAWLERS = {
    "fpt": [
        "fpt_crawl/fpt_crawl_ip.py",
        "fpt_crawl/fpt_crawl_ss.py",
        "fpt_crawl/fpt_crawl_oppo.py",
        "fpt_crawl/fpt_crawl_xiaomi.py",
    ],
    "tgdd": [
        "tgdd_crawl/tgdd_crawl_ip.py",
        "tgdd_crawl/tgdd_crawl_ss.py",
        "tgdd_crawl/tgdd_crawl_oppo.py",
        "tgdd_crawl/tgdd_crawl_xiaomi.py",
    ],
    "dmx": [
        "dmx_crawl/dmx_crawl_ip.py",
        "dmx_crawl/dmx_crawl_ss.py",
        "dmx_crawl/dmx_crawl_oppo.py",
        "dmx_crawl/dmx_crawl_xiaomi.py",
    ]
}

# Thiết lập logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/scheduler_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_separator():
    """In đường phân cách"""
    logger.info("=" * 70)

def run_crawler(script_path):
    """Chạy một script crawler"""
    try:
        logger.info(f"🚀 Đang chạy: {script_path}")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=1800  # Timeout 30 phút
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Hoàn tất: {script_path}")
            return True
        else:
            logger.error(f"❌ Lỗi {script_path}: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ Timeout: {script_path}")
        return False
    except Exception as e:
        logger.error(f"❌ Exception {script_path}: {str(e)}")
        return False

def crawl_all():
    """Crawl tất cả các sàn"""
    log_separator()
    logger.info("🔄 BẮT ĐẦU CRAWL TỰ ĐỘNG")
    logger.info(f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_separator()
    
    total = 0
    success = 0
    
    for platform, scripts in CRAWLERS.items():
        logger.info(f"\n🏪 Platform: {platform.upper()}")
        for script in scripts:
            if os.path.exists(script):
                total += 1
                if run_crawler(script):
                    success += 1
                time.sleep(2)  # Delay giữa các lần crawl
            else:
                logger.warning(f"⚠️ Không tìm thấy: {script}")
    
    log_separator()
    logger.info(f"📊 THỐNG KÊ: {success}/{total} crawler thành công")
    logger.info(f"⏰ Lần crawl tiếp theo: sau {CRAWL_INTERVAL_HOURS} giờ")
    log_separator()

def crawl_single_platform(platform):
    """Crawl một platform cụ thể"""
    if platform not in CRAWLERS:
        logger.error(f"❌ Platform không hợp lệ: {platform}")
        logger.info(f"Các platform hợp lệ: {', '.join(CRAWLERS.keys())}")
        return
    
    logger.info(f"\n🏪 Đang crawl {platform.upper()}")
    for script in CRAWLERS[platform]:
        if os.path.exists(script):
            run_crawler(script)
            time.sleep(2)
        else:
            logger.warning(f"⚠️ Không tìm thấy: {script}")

def crawl_single_brand(brand):
    """Crawl một brand cụ thể từ tất cả platform"""
    brand_files = {
        "iphone": ["ip.py", "ip.py"],
        "samsung": ["ss.py", "ss.py"],
        "oppo": ["oppo.py", "oppo.py"],
        "xiaomi": ["xiaomi.py", "xiaomi.py"]
    }
    
    if brand not in brand_files:
        logger.error(f"❌ Brand không hợp lệ: {brand}")
        logger.info(f"Các brand hợp lệ: {', '.join(brand_files.keys())}")
        return
    
    logger.info(f"\n📱 Đang crawl {brand.upper()}")
    for platform, scripts in CRAWLERS.items():
        for script in scripts:
            if brand.lower() in script.lower() and os.path.exists(script):
                run_crawler(script)
                time.sleep(2)

def show_status():
    """Hiển thị trạng thái scheduler"""
    logger.info("\n" + "=" * 50)
    logger.info("📋 TRẠNG THÁI SCHEDULER")
    logger.info("=" * 50)
    logger.info(f"🔄 Chế độ: {'Auto' if schedule.jobs else 'Manual'}")
    logger.info(f"⏰ Crawl mỗi: {CRAWL_INTERVAL_HOURS} giờ")
    logger.info(f"📅 Crawl hàng ngày lúc: {CRAWL_TIME}")
    logger.info(f"🕐 Hiện tại: {datetime.now().strftime('%H:%M:%S')}")
    logger.info("\n📦 Các crawler sẵn có:")
    for platform, scripts in CRAWLERS.items():
        existing = [s for s in scripts if os.path.exists(s)]
        logger.info(f"   {platform.upper()}: {len(existing)}/{len(scripts)} scripts")
    logger.info("=" * 50)

def menu():
    """Hiển thị menu tương tác"""
    while True:
        print("\n" + "=" * 50)
        print("🤖 AI PRICE COMPARISON - SCHEDULER")
        print("=" * 50)
        print("1. 🚀 Crawl tất cả ngay")
        print("2. 🏪 Crawl theo platform (fpt/tgdd/dmx)")
        print("3. 📱 Crawl theo brand (iphone/samsung/oppo/xiaomi)")
        print("4. 🔄 Chạy scheduler tự động")
        print("5. 📊 Xem trạng thái")
        print("6. ❌ Thoát")
        print("=" * 50)
        
        choice = input("\nChọn chức năng (1-6): ").strip()
        
        if choice == "1":
            crawl_all()
        elif choice == "2":
            platform = input("Nhập platform (fpt/tgdd/dmx): ").strip().lower()
            crawl_single_platform(platform)
        elif choice == "3":
            brand = input("Nhập brand (iphone/samsung/oppo/xiaomi): ").strip().lower()
            crawl_single_brand(brand)
        elif choice == "4":
            start_scheduler()
        elif choice == "5":
            show_status()
        elif choice == "6":
            logger.info("👋 Đã thoát scheduler!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ!")

def start_scheduler():
    """Khởi động scheduler tự động"""
    logger.info("\n🤖 ĐANG KHỞI ĐỘNG SCHEDULER TỰ ĐỘNG")
    logger.info(f"⏰ Cài đặt: Crawl mỗi {CRAWL_INTERVAL_HOURS} giờ")
    logger.info(f"🌙 Crawl hàng ngày lúc: {CRAWL_TIME}")
    logger.info("🛑 Nhấn Ctrl+C để dừng\n")
    
    # Lập lịch crawl
    schedule.every(CRAWL_INTERVAL_HOURS).hours.do(crawl_all)
    schedule.every().day.at(CRAWL_TIME).do(crawl_all)
    
    # Crawl ngay lần đầu
    crawl_all()
    
    # Chạy vòng lặp
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Kiểm tra mỗi phút
    except KeyboardInterrupt:
        logger.info("\n🛑 Scheduler đã dừng!")

def print_banner():
    """In banner khởi động"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║           🤖 AI PRICE COMPARISON SCHEDULER              ║
    ║       Tự động cập nhật giá từ các sàn TMĐT             ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

if __name__ == "__main__":
    print_banner()
    
    # Kiểm tra tham số command line
    import argparse
    parser = argparse.ArgumentParser(description='AI Price Comparison Scheduler')
    parser.add_argument('--mode', '-m', choices=['auto', 'manual', 'once'], 
                        default='manual', help='Chế độ chạy')
    parser.add_argument('--platform', '-p', choices=['fpt', 'tgdd', 'dmx', 'all'],
                        help='Crawl platform cụ thể')
    parser.add_argument('--brand', '-b', choices=['iphone', 'samsung', 'oppo', 'xiaomi'],
                        help='Crawl brand cụ thể')
    
    args = parser.parse_args()
    
    if args.mode == 'auto':
        start_scheduler()
    elif args.mode == 'once':
        if args.platform and args.platform != 'all':
            crawl_single_platform(args.platform)
        elif args.brand:
            crawl_single_brand(args.brand)
        else:
            crawl_all()
    else:
        menu()
