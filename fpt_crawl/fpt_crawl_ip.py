import time
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
import json

# --- CẤU HÌNH ---
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

client = MongoClient("mongodb://localhost:27017/")
db = client["fpt_database"]
collection = db["iphone_full_data"]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def clean_price(price_str):
    try:
        price_clean = re.sub(r'[^\d]', '', price_str)
        return int(price_clean) if price_clean else 0
    except:
        return 0

def extract_product_from_card(card_html, base_url):
    soup = BeautifulSoup(card_html, 'html.parser')
    try:
        all_links = soup.find_all('a', href=True)
        product_link = None
        for link in all_links:
            href = link.get('href', '')
            if '/dien-thoai/iphone' in href.lower():
                product_link = base_url + href if href.startswith('/') else href
                break
        
        if not product_link:
            return None
        
        name_elem = soup.find('h3') or soup.find('h2') or soup.find('p', class_=re.compile(r'name|title', re.I))
        name = name_elem.get_text(strip=True) if name_elem else "Không có tên"
        
        price_elem = None
        price_selectors = ['p[class*="b1-semibold"]', 'p[class*="price"]', 'span[class*="price"]']
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                break
        
        price_text = price_elem.get_text(strip=True) if price_elem else "0đ"
        price_num = clean_price(price_text)
        
        img_elem = soup.find('img')
        img_url = img_elem.get('src') or img_elem.get('data-src', '') if img_elem else ""
        if img_url and not img_url.startswith('http'):
            img_url = base_url + img_url
        
        return {
            "name": name,
            "price_display": price_text,
            "price_number": price_num,
            "url": product_link,
            "image": img_url
        }
    except:
        return None

def crawl_fpt_iphone_full():
    driver = get_driver()
    try:
        url_main = "https://fptshop.com.vn/dien-thoai/apple-iphone"
        driver.get(url_main)
        print(f"🚀 Bắt đầu quét giá iPhone: {url_main}")
        
        time.sleep(5)
        
        # Cuộn trang & Click xem thêm
        for _ in range(8):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Xem thêm')]")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
            except:
                pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.find_all('div', class_=re.compile(r'group relative|ProductCard|product', re.I))
        
        product_list = []
        scraped_links = set()
        
        for card in cards:
            product = extract_product_from_card(str(card), "https://fptshop.com.vn")
            if product and product['url'] not in scraped_links:
                if 'iphone' in product['name'].lower():
                    product_list.append(product)
                    scraped_links.add(product['url'])
                    print(f"✓ {product['name'][:40]} - {product['price_display']}")

        # XỬ LÝ LƯU MONGODB + CRAWL COMMENTS
        today = datetime.now().strftime("%Y-%m-%d")
        updated = 0
        
        for idx, p in enumerate(product_list, 1):
            try:
                print(f"\n[{idx}/{len(product_list)}] Crawl comments: {p['name'][:50]}")
                
                # Vào trang chi tiết để lấy comments
                driver.get(p['url'])
                time.sleep(3)
                
                # Cuộn xuống phần comments
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
                time.sleep(2)
                
                # Tìm comments
                page_detail = driver.page_source
                soup_detail = BeautifulSoup(page_detail, "html.parser")
                
                comments = []
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
                
                # Cập nhật MongoDB với comments
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
                updated += 1
                print(f"   ✅ Đã cập nhật")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"   ⚠️ Lỗi: {str(e)[:100]}")
                continue
        
        print(f"\n✅ HOÀN TẤT! Đã cập nhật {updated} sản phẩm iPhone vào database.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_fpt_iphone_full()
