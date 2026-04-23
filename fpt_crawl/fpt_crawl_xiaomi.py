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
import json

# --- CẤU HÌNH ---
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

client = MongoClient("mongodb://localhost:27017/")
db = client["fpt_database"]
collection = db["xiaomi_full_data"]  # Collection riêng cho Xiaomi

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--headless")  # Chạy ẩn để nhanh hơn
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def clean_price(price_str):
    """Chuyển đổi giá text sang số nguyên"""
    try:
        price_clean = re.sub(r'[^\d]', '', price_str)
        return int(price_clean) if price_clean else 0
    except:
        return 0

def extract_product_from_card(card_html, base_url):
    """Trích xuất thông tin sản phẩm từ card HTML"""
    soup = BeautifulSoup(card_html, 'html.parser')
    
    try:
        # Tìm link sản phẩm
        all_links = soup.find_all('a', href=True)
        product_link = None
        for link in all_links:
            href = link.get('href', '')
            # Tìm link chứa /dien-thoai/xiaomi- hoặc /dien-thoai/xiaomi/
            if '/dien-thoai/xiaomi-' in href or '/dien-thoai/xiaomi/' in href:
                if href.startswith('/'):
                    product_link = base_url + href
                else:
                    product_link = href
                break
        
        if not product_link:
            return None
        
        # Tìm tên sản phẩm
        name_elem = soup.find('h3') or soup.find('h2') or soup.find('p', class_=re.compile(r'name|title', re.I))
        name = name_elem.get_text(strip=True) if name_elem else "Không có tên"
        
        # Tìm giá
        price_elem = None
        price_selectors = [
            'p[class*="b1-semibold"]',
            'p[class*="price"]',
            'span[class*="price"]',
            'div[class*="price"]'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                break
        
        # Nếu không tìm thấy, tìm text chứa giá
        if not price_elem:
            all_text = soup.get_text()
            price_match = re.search(r'(\d{1,3}(?:\.\d{3})*\.?\d*)đ', all_text)
            if price_match:
                price_text = price_match.group(1) + 'đ'
                price_num = clean_price(price_text)
                return {
                    "name": name,
                    "price_display": price_text,
                    "price_number": price_num,
                    "url": product_link,
                    "image": ""
                }
        
        price_text = price_elem.get_text(strip=True) if price_elem else "0đ"
        price_num = clean_price(price_text)
        
        # Tìm ảnh
        img_elem = soup.find('img')
        img_url = ""
        if img_elem:
            img_url = img_elem.get('src') or img_elem.get('data-src', '')
            if img_url and not img_url.startswith('http'):
                img_url = base_url + img_url
        
        return {
            "name": name,
            "price_display": price_text,
            "price_number": price_num,
            "url": product_link,
            "image": img_url
        }
        
    except Exception as e:
        print(f"Lỗi extract product: {e}")
        return None

def crawl_fpt_xiaomi_price_only():
    driver = get_driver()
    try:
        url_main = "https://fptshop.com.vn/dien-thoai/xiaomi"
        driver.get(url_main)
        print(f"🚀 Bắt đầu quét giá Xiaomi: {url_main}")
        
        # Chờ trang load
        time.sleep(5)
        
        # Cuộn trang để load hết sản phẩm
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < 10:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Thử click nút "Xem thêm" nếu có
            try:
                xem_them_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Xem thêm')]")
                for btn in xem_them_btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        print("Đã click Xem thêm")
                        time.sleep(2)
            except:
                pass
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
        
        # Lấy HTML của trang
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Tìm card sản phẩm
        cards = soup.find_all('div', class_=re.compile(r'group relative'))
        
        if not cards:
            cards = soup.find_all('div', class_=re.compile(r'ProductCard', re.I))
        
        if not cards:
            cards = soup.find_all('div', class_=re.compile(r'product', re.I))
        
        print(f"📦 Tìm thấy {len(cards)} card sản phẩm tiềm năng")
        
        product_list = []
        scraped_links = set()
        
        for card in cards:
            product = extract_product_from_card(str(card), "https://fptshop.com.vn")
            if product and product['url'] not in scraped_links:
                # Kiểm tra tên có chứa Xiaomi không
                if 'xiaomi' in product['name'].lower() or 'xiaomi' in product['url'].lower():
                    product_list.append(product)
                    scraped_links.add(product['url'])
                    print(f"✓ {product['name'][:50]} - {product['price_display']}")
        
        # Nếu không tìm thấy, thử từ JSON
        if len(product_list) == 0:
            print("Không tìm thấy card, thử tìm trong script JSON...")
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and '"items":' in script.string:
                    try:
                        json_match = re.search(r'({.*"items":.*})', script.string, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            if 'items' in data:
                                for item in data['items']:
                                    product_name = item.get('name', item.get('displayName', ''))
                                    if 'xiaomi' in product_name.lower():
                                        product_list.append({
                                            "name": product_name,
                                            "price_display": f"{item.get('currentPrice', 0):,}đ" if item.get('currentPrice') else "0đ",
                                            "price_number": item.get('currentPrice', 0),
                                            "url": f"https://fptshop.com.vn/dien-thoai/{item.get('slug', '')}",
                                            "image": item.get('image', {}).get('src', '') if isinstance(item.get('image'), dict) else item.get('image', '')
                                        })
                        break
                    except Exception as e:
                        print(f"Lỗi parse JSON: {e}")
                        continue
        
        print(f"\n--- Tìm thấy {len(product_list)} sản phẩm Xiaomi ---")
        
        if len(product_list) == 0:
            print("⚠️ KHÔNG TÌM THẤY SẢN PHẨM!")
            return
        
        # Cập nhật giá cho từng sản phẩm
        today = datetime.now().strftime("%Y-%m-%d")
        updated = 0
        
        for idx, p in enumerate(product_list, 1):
            try:
                print(f"\n📱 [{idx}/{len(product_list)}] {p['name'][:50]}")
                print(f"   💰 Giá hiện tại: {p['price_display']}")
                
                # Kiểm tra xem đã có price_history của ngày hôm nay chưa
                existing_record = collection.find_one({
                    "url": p["url"],
                    "price_history.date": today
                })
                
                if existing_record:
                    # Nếu đã có ngày hôm nay, cập nhật lại giá (đè lên)
                    result = collection.update_one(
                        {"url": p["url"], "price_history.date": today},
                        {
                            "$set": {
                                "name": p["name"],
                                "price_display": p["price_display"],
                                "price_number": p["price_number"],
                                "image": p["image"],
                                "price_history.$.price": p["price_number"],
                                "last_price_update": datetime.now(),
                                "last_crawl_date": today
                            }
                        }
                    )
                    print(f"   🔄 Đã cập nhật giá ngày {today} (đè lên giá cũ)")
                else:
                    # Nếu chưa có, thêm mới vào price_history
                    result = collection.update_one(
                        {"url": p["url"]},
                        {
                            "$set": {
                                "name": p["name"],
                                "price_display": p["price_display"],
                                "price_number": p["price_number"],
                                "image": p["image"],
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
                    print(f"   ✅ Đã thêm giá mới vào price_history ngày {today}")
                
                updated += 1
                
                # Delay nhẹ để tránh quá tải
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Lỗi: {str(e)[:100]}")
                continue
        
        print(f"\n{'='*70}")
        print(f"✅ HOÀN TẤT CẬP NHẬT GIÁ!")
        print(f"📊 Thống kê:")
        print(f"   - Tổng sản phẩm: {len(product_list)}")
        print(f"   - Đã cập nhật giá: {updated}")
        print(f"   - Ngày cập nhật: {today}")
        
    except Exception as e:
        print(f"Lỗi chính: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*70)
        print("🏁 HOÀN TẤT!")
        print("⏳ Đợi 3 giây trước khi đóng trình duyệt...")
        time.sleep(3)
        driver.quit()
        print("👋 Đã đóng trình duyệt")

if __name__ == "__main__":
    print("🌟 BẮT ĐẦU CẬP NHẬT GIÁ XIAOMI TỪ FPT SHOP 🌟")
    print("⏳ Quá trình có thể mất vài phút...")
    print("="*70)
    crawl_fpt_xiaomi_price_only()