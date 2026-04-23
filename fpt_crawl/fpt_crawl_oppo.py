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
collection = db["oppo_full_data"]  # Collection riêng cho OPPO

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # chrome_options.add_argument("--headless")  # Bỏ comment để chạy ngầm
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
            # Tìm link chứa /dien-thoai/oppo- hoặc /dien-thoai/oppo/
            if '/dien-thoai/oppo-' in href or '/dien-thoai/oppo/' in href:
                if href.startswith('/'):
                    product_link = base_url + href
                else:
                    product_link = href
                break
        
        if not product_link:
            return None
        
        # Tìm tên sản phẩm (thường trong thẻ h3)
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

def crawl_fpt_oppo_update():
    driver = get_driver()
    try:
        url_main = "https://fptshop.com.vn/dien-thoai/oppo"
        driver.get(url_main)
        print(f"--- Đang quét: {url_main} ---")
        
        # Chờ trang load
        wait = WebDriverWait(driver, 15)
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
        product_cards = []
        
        # Tìm theo class chứa "group relative" (đặc điểm của card sản phẩm)
        cards = soup.find_all('div', class_=re.compile(r'group relative'))
        
        if not cards:
            # Thử tìm theo class chứa "ProductCard"
            cards = soup.find_all('div', class_=re.compile(r'ProductCard', re.I))
        
        if not cards:
            # Thử tìm theo class chứa "product"
            cards = soup.find_all('div', class_=re.compile(r'product', re.I))
        
        print(f"Tìm thấy {len(cards)} card sản phẩm tiềm năng")
        
        product_list = []
        scraped_links = set()
        
        for card in cards:
            product = extract_product_from_card(str(card), "https://fptshop.com.vn")
            if product and product['url'] not in scraped_links:
                # Kiểm tra tên có chứa OPPO không
                if 'oppo' in product['name'].lower() or 'oppo' in product['url'].lower():
                    product_list.append(product)
                    scraped_links.add(product['url'])
                    print(f"✓ {product['name'][:50]} - {product['price_display']}")
        
        # Nếu vẫn không tìm thấy, thử cách khác: lấy từ data JSON trong script
        if len(product_list) == 0:
            print("Không tìm thấy card, thử tìm trong script JSON...")
            
            # Tìm script chứa dữ liệu sản phẩm
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and '"items":' in script.string and ('product' in script.string or 'OPPO' in script.string):
                    try:
                        # Trích xuất JSON
                        json_match = re.search(r'({.*"items":.*})', script.string, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            if 'items' in data:
                                for item in data['items']:
                                    if 'sku' in item or 'name' in item:
                                        product_name = item.get('name', item.get('displayName', ''))
                                        if 'oppo' in product_name.lower():
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
        
        print(f"\n--- Tìm thấy {len(product_list)} sản phẩm OPPO ---")
        
        if len(product_list) == 0:
            print("⚠️ KHÔNG TÌM THẤY SẢN PHẨM! Lưu HTML để debug...")
            with open("debug_oppo_page.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            return
        
        # Crawl chi tiết từng sản phẩm
        today = datetime.now().strftime("%Y-%m-%d")
        
        for idx, p in enumerate(product_list, 1):
            try:
                print(f"\n[{idx}/{len(product_list)}] Đang xử lý: {p['name'][:50]}")
                driver.get(p['url'])
                time.sleep(3)
                
                # Cuộn để load comments
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
                time.sleep(2)
                
                # Tìm comments
                page_detail = driver.page_source
                soup_detail = BeautifulSoup(page_detail, "html.parser")
                
                comments = []
                
                # Tìm comments trong các span hoặc div
                comment_selectors = [
                    'span[class*="break-word"]',
                    'div[class*="comment"]',
                    'p[class*="comment"]',
                    'div[class*="review"]',
                    'div[data-testid*="comment"]',
                    'div[class*="feedback"]',
                    'div[class*="danh-gia"]'
                ]
                
                for selector in comment_selectors:
                    cmt_elements = soup_detail.select(selector)
                    if cmt_elements:
                        for cmt in cmt_elements[:20]:
                            txt = cmt.get_text().strip()
                            if len(txt) > 10 and len(txt) < 500:
                                comments.append(txt)
                        if comments:
                            break
                
                print(f"   Tìm thấy {len(comments)} bình luận")
                
                # Cập nhật MongoDB
                result = collection.update_one(
                    {"url": p["url"]},
                    {
                        "$set": {
                            "name": p["name"],
                            "price_display": p["price_display"],
                            "price_number": p["price_number"],
                            "image": p["image"],
                            "last_updated": datetime.now()
                        },
                        "$addToSet": {"comments": {"$each": comments[:50]}},
                        "$push": {
                            "price_history": {
                                "date": today,
                                "price": p["price_number"]
                            }
                        }
                    },
                    upsert=True
                )
                print(f"   ✅ Đã cập nhật - Giá: {p['price_display']}")
                
                # Thêm delay để tránh bị chặn
                time.sleep(2)
                
            except Exception as e:
                print(f"   ⚠️ Lỗi: {str(e)[:100]}")
                continue
                
        print(f"\n✅ HOÀN TẤT! Đã xử lý {len(product_list)} sản phẩm OPPO")
        
    except Exception as e:
        print(f"Lỗi chính: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_fpt_oppo_update()