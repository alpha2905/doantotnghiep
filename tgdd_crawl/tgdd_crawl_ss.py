import time
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient

# --- CẤU HÌNH ---
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

client = MongoClient("mongodb://localhost:27017/")
db = client["tgdd_database"]
collection = db["samsung_master_data"]

def get_driver():
    """Khởi tạo Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Chạy ẩn để tăng tốc
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def crawl_tgdd_samsung_prices():
    """Crawl giá Samsung từ TGDĐ và cập nhật vào database"""
    driver = get_driver()
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        print(f"🚀 Bắt đầu quét giá Samsung từ TGDĐ")
        print(f"📅 Ngày cập nhật: {today}")
        print(f"🔗 URL: https://www.thegioididong.com/dtdd-samsung")
        
        driver.get("https://www.thegioididong.com/dtdd-samsung")
        time.sleep(5)
        
        # Click nút "Xem thêm" nếu có
        click_count = 0
        while True:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "see-more-btn"))
                )
                driver.execute_script("arguments[0].click();", btn)
                click_count += 1
                print(f"  🔄 Đã click Xem thêm lần thứ {click_count}")
                time.sleep(2)
            except:
                break

        # Cuộn trang để load hết sản phẩm
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.find_all("li", class_="item")
        
        print(f"📦 Tìm thấy {len(items)} sản phẩm Samsung")
        
        product_list = []
        for it in items:
            a_tag = it.find("a", class_="main-contain")
            if not a_tag: 
                continue
            
            # Lấy giá
            raw_price = a_tag.get("data-price") or "0"
            try:
                price_number = int(float(raw_price))
            except:
                price_number = 0
            
            # Lấy tên
            name = a_tag.get("data-name") or "Unknown"
            
            # Lấy URL
            href = a_tag.get("href", "")
            url = "https://www.thegioididong.com" + href if href.startswith("/") else href
            
            # Lấy ảnh
            img_tag = it.find("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("src") or img_tag.get("data-src", "")
            
            # Lấy ID
            tgdd_id = a_tag.get("data-id")
            
            product_list.append({
                "tgdd_id": tgdd_id,
                "name": name,
                "price_number": price_number,
                "price_display": f"{price_number:,.0f}đ" if price_number > 0 else "Liên hệ",
                "url": url,
                "image": img_url
            })
            
            print(f"  ✓ {name[:50]} - {price_number:,.0f}đ")
        
        print(f"\n--- Cập nhật giá cho {len(product_list)} sản phẩm Samsung ---")
        
        updated = 0
        for idx, p in enumerate(product_list, 1):
            try:
                if not p["tgdd_id"]:
                    print(f"  ⚠️ [{idx}] {p['name'][:40]} - Không có ID, bỏ qua")
                    continue
                
                # Kiểm tra xem đã có price_history của ngày hôm nay chưa
                existing_record = collection.find_one({
                    "tgdd_id": p["tgdd_id"],
                    "price_history.date": today
                })
                
                if existing_record:
                    # Nếu đã có ngày hôm nay, cập nhật lại giá (đè lên)
                    result = collection.update_one(
                        {"tgdd_id": p["tgdd_id"], "price_history.date": today},
                        {
                            "$set": {
                                "name": p["name"],
                                "price_number": p["price_number"],
                                "price_display": p["price_display"],
                                "image": p["image"],
                                "price_history.$.price": p["price_number"],
                                "last_price_update": datetime.now(),
                                "last_crawl_date": today
                            }
                        }
                    )
                    print(f"  🔄 [{idx}] {p['name'][:40]} - Cập nhật giá ngày {today}")
                else:
                    # Nếu chưa có, thêm mới vào price_history
                    result = collection.update_one(
                        {"tgdd_id": p["tgdd_id"]},
                        {
                            "$set": {
                                "name": p["name"],
                                "price_number": p["price_number"],
                                "price_display": p["price_display"],
                                "image": p["image"],
                                "url": p["url"],
                                "last_price_update": datetime.now(),
                                "last_crawl_date": today
                            },
                            "$push": {
                                "price_history": {
                                    "date": today,
                                    "price": p["price_number"]
                                }
                            }
                        },
                        upsert=True
                    )
                    print(f"  ✅ [{idx}] {p['name'][:40]} - Thêm giá mới ngày {today}")
                
                updated += 1
                time.sleep(0.3)  # Delay nhẹ
                
            except Exception as e:
                print(f"  ❌ [{idx}] Lỗi: {str(e)[:80]}")
                continue
        
        print(f"\n{'='*70}")
        print(f"✅ HOÀN TẤT CẬP NHẬT GIÁ SAMSUNG TỪ TGDĐ!")
        print(f"📊 Thống kê:")
        print(f"   - Tổng sản phẩm: {len(product_list)}")
        print(f"   - Đã cập nhật giá: {updated}")
        print(f"   - Ngày cập nhật: {today}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"❌ Lỗi chính: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Đóng trình duyệt...")
        time.sleep(2)
        driver.quit()
        print("👋 Kết thúc!")

def show_statistics():
    """Hiển thị thống kê tổng quan database Samsung"""
    try:
        total_products = collection.count_documents({})
        
        # Lấy ngày cập nhật gần nhất
        latest = collection.find_one(sort=[("last_crawl_date", -1)])
        last_crawl = latest.get("last_crawl_date", "Chưa có") if latest else "Chưa có"
        
        # Tổng số price_history entries
        pipeline = [
            {"$project": {"history_count": {"$size": {"$ifNull": ["$price_history", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$history_count"}}}
        ]
        result = list(collection.aggregate(pipeline))
        total_history = result[0]["total"] if result else 0
        
        print("\n📊 THỐNG KÊ DATABASE SAMSUNG (TGDĐ):")
        print("-" * 50)
        print(f"   Tổng số sản phẩm: {total_products}")
        print(f"   Tổng số lần cập nhật giá: {total_history}")
        print(f"   Lần cập nhật cuối: {last_crawl}")
        print("-" * 50)
        
    except Exception as e:
        print(f"Lỗi thống kê: {e}")

def show_sample_products():
    """Hiển thị mẫu 5 sản phẩm Samsung trong database"""
    products = list(collection.find({}, {"name": 1, "price_display": 1, "price_history": 1}).limit(5))
    
    if not products:
        print("⚠️ Database Samsung trống!")
        return
    
    print("\n📋 MẪU SẢN PHẨM SAMSUNG TRONG DATABASE:")
    print("-" * 70)
    for i, p in enumerate(products, 1):
        history_count = len(p.get("price_history", []))
        print(f"{i}. {p['name'][:50]}")
        print(f"   💰 Giá hiện tại: {p.get('price_display', 'N/A')}")
        print(f"   📊 Lịch sử giá: {history_count} ngày")
        print()

def crawl_initial_products():
    """Crawl lần đầu để lấy danh sách sản phẩm Samsung từ TGDĐ"""
    driver = get_driver()
    try:
        print("--- Đang quét danh sách Samsung từ TGDĐ ---")
        driver.get("https://www.thegioididong.com/dtdd-samsung")
        
        # Click nút "Xem thêm" nếu có
        while True:
            try:
                wait = WebDriverWait(driver, 5)
                btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "see-more-btn")))
                driver.execute_script("arguments[0].click();", btn)
                print("   Đã click Xem thêm")
                time.sleep(2)
            except: 
                break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.find_all("li", class_="item")
        
        today = datetime.now().strftime("%Y-%m-%d")
        product_list = []
        
        for it in items:
            a_tag = it.find("a", class_="main-contain")
            if not a_tag: 
                continue
            
            # Lấy giá
            raw_price = a_tag.get("data-price") or "0"
            try:
                price_number = int(float(raw_price))
            except:
                price_number = 0
            
            # Lấy tên
            name = a_tag.get("data-name") or "Unknown"
            
            # Lấy URL
            href = a_tag.get("href", "")
            url = "https://www.thegioididong.com" + href if href.startswith("/") else href
            
            # Lấy ảnh
            img_tag = it.find("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("src") or img_tag.get("data-src", "")
            
            product_list.append({
                "tgdd_id": a_tag.get("data-id"),
                "name": name,
                "price_number": price_number,
                "price_display": f"{price_number:,.0f}đ" if price_number > 0 else "Liên hệ",
                "url": url,
                "image": img_url,
                "price_history": [{"date": today, "price": price_number}],
                "last_crawl_date": today,
                "last_price_update": datetime.now()
            })
        
        print(f"=> Tìm thấy {len(product_list)} mẫu Samsung")
        
        # Lưu vào database
        for product in product_list:
            if product["tgdd_id"]:
                collection.update_one(
                    {"tgdd_id": product["tgdd_id"]},
                    {"$set": product},
                    upsert=True
                )
                print(f"  ✅ Đã lưu: {product['name'][:50]}")
        
        print(f"\n✅ Đã lưu {len(product_list)} sản phẩm Samsung vào database!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    print("🌟 CẬP NHẬT GIÁ SAMSUNG TỪ THẾ GIỚI DI ĐỘNG 🌟")
    print("="*70)
    
    # Kiểm tra database có sản phẩm chưa
    total_products = collection.count_documents({})
    
    if total_products == 0:
        print("⚠️ Database trống! Đang crawl danh sách sản phẩm lần đầu...")
        crawl_initial_products()
    
    # Hiển thị thống kê
    show_statistics()
    
    # Hiển thị mẫu sản phẩm
    show_sample_products()
    
    # Xác nhận
    confirm = input("\n🔄 Bắt đầu cập nhật giá hôm nay? (y/n): ")
    if confirm.lower() == 'y':
        print("\n⚠️ Trình duyệt chạy ẩn (headless) để tăng tốc!")
        print("⏳ Quá trình có thể mất vài phút...")
        print("="*70)
        crawl_tgdd_samsung_prices()
    else:
        print("❌ Đã hủy!")