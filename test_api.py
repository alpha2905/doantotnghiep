# test_api.py
"""
Script test API cho hệ thống so sánh giá
Chạy: python test_api.py
"""

import requests
import json
import sys
from datetime import datetime

# === CẤU HÌNH ===
BASE_URL = "http://127.0.0.1:8000"
API_ENDPOINT = f"{BASE_URL}/api/compare"

# Test cases
TEST_CASES = [
    {"brand": "iphone", "name": "iPhone 15 Pro Max"},
    {"brand": "iphone", "name": "iPhone 16 Pro Max"},
    {"brand": "samsung", "name": "Samsung Galaxy S24 Ultra"},
    {"brand": "oppo", "name": "OPPO Find X7"},
    {"brand": "xiaomi", "name": "Xiaomi 14"},
]

def print_separator():
    print("=" * 70)

def test_health():
    """Test API health"""
    print("🩺 Kiểm tra API Health...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API đang chạy!")
            return True
        else:
            print(f"⚠️  API trả về status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Không kết nối được đến API!")
        print("💡 Hãy chạy: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_compare_api(brand, name):
    """Test API so sánh giá"""
    print(f"\n🔍 Test: {brand.upper()} - {name}")
    print("-" * 50)
    
    try:
        params = {"brand": brand, "name": name}
        response = requests.get(API_ENDPOINT, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Lỗi HTTP {response.status_code}")
            return False
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            print("⚠️  Không tìm thấy sản phẩm nào")
            return False
        
        print(f"✅ Tìm thấy {len(results)} kết quả:")
        
        for item in results:
            platform = item.get("platform", "N/A")
            product_name = item.get("name", "N/A")
            price = item.get("current_price", 0)
            forecast = item.get("forecast", 0)
            
            print(f"\n   🏪 {platform}:")
            print(f"      📱 {product_name[:50]}...")
            print(f"      💰 Giá: {price:,}đ")
            print(f"      🔮 Dự báo: {forecast:,}đ")
            
            # Sentiment
            sentiment = item.get("sentiment", {})
            pos = sentiment.get("pos", 0)
            neg = sentiment.get("neg", 0)
            neu = sentiment.get("neu", 0)
            print(f"      😊 Sentiment: +{pos}% / -{neg}% / ~{neu}%")
            
            # Comments
            comments = sentiment.get("list", [])
            if comments:
                print(f"      💬 {len(comments)} bình luận được phân tích")
        
        return True
        
    except requests.exceptions.Timeout:
        print("⏱️  Request timeout!")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_all():
    """Chạy tất cả test cases"""
    print_separator()
    print("🧪 AI PRICE COMPARISON - API TEST")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()
    
    # Kiểm tra API health trước
    if not test_health():
        sys.exit(1)
    
    print_separator()
    
    # Chạy test cases
    passed = 0
    failed = 0
    
    for test in TEST_CASES:
        if test_compare_api(test["brand"], test["name"]):
            passed += 1
        else:
            failed += 1
        time.sleep(1)  # Delay giữa các request
    
    # Kết quả
    print_separator()
    print("📊 TỔNG KẾT:")
    print(f"   ✅ Thành công: {passed}/{len(TEST_CASES)}")
    print(f"   ❌ Thất bại: {failed}/{len(TEST_CASES)}")
    print_separator()
    
    if failed == 0:
        print("🎉 Tất cả tests đều thành công!")
    else:
        print("⚠️  Một số tests thất bại!")
    
    return failed == 0

def interactive_test():
    """Test tương tác"""
    print_separator()
    print("🎮 CHẾ ĐỘ TEST TƯƠNG TÁC")
    print_separator()
    
    brands = ["iphone", "samsung", "oppo", "xiaomi"]
    
    while True:
        print("\nChọn hãng:")
        for i, brand in enumerate(brands, 1):
            print(f"  {i}. {brand.upper()}")
        print("  0. Thoát")
        
        choice = input("\nChọn (0-4): ").strip()
        
        if choice == "0":
            break
        
        try:
            brand_idx = int(choice) - 1
            if 0 <= brand_idx < len(brands):
                brand = brands[brand_idx]
                name = input(f"Nhập tên sản phẩm {brand.upper()}: ").strip()
                if name:
                    test_compare_api(brand, name)
            else:
                print("❌ Lựa chọn không hợp lệ!")
        except ValueError:
            print("❌ Vui lòng nhập số!")

if __name__ == "__main__":
    import time
    import argparse
    
    parser = argparse.ArgumentParser(description='Test API for AI Price Comparison')
    parser.add_argument('--interactive', '-i', action='store_true', 
                        help='Chế độ test tương tác')
    parser.add_argument('--brand', '-b', help='Test một brand cụ thể')
    parser.add_argument('--name', '-n', help='Tên sản phẩm cần test')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_test()
    elif args.brand and args.name:
        print_separator()
        print("🧪 API TEST - SINGLE")
        print_separator()
        test_health()
        test_compare_api(args.brand, args.name)
    else:
        success = test_all()
        sys.exit(0 if success else 1)
