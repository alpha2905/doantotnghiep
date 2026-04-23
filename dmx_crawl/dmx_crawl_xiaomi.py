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

# --- KHẮC PHỤC LỖI PROXY HỆ THỐNG ---
for key in ["http_proxy", "https_proxy", "no_proxy"]:
    if key in os.environ: del os.environ[key]

# --- KẾT NỐI MONGODB ---
client = MongoClient("mongodb://localhost:27017/")
db = client["dmx_database"]
collection = db["xiaomi_products"]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    chrome_options.add_argument('--proxy-server="direct://"')
    chrome_options.add_argument('--proxy-bypass-list=*')
    chrome_options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def clean_price(price_str):
    """Chuyển '6.990.000₫' thành 6990000"""
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def get_all_comments_by_clicking(driver, review_url):
    """Lấy bình luận từ tối đa 10 trang bằng cách nhấn nút Next"""
    all_comments = []
    current_page = 1
    max_pages = 10
    
    print(f"  🌐 Đang mở trang đánh giá: {review_url}")
    driver.get(review_url)
    time.sleep(4)
    
    while current_page <= max_pages:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cmt_elements = soup.select("p.cmt-txt") or soup.select(".cmt-txt, .comment-text, .review-text")
        
        if cmt_elements:
            page_comments = []
            for cmt in cmt_elements:
                txt = re.sub(r'\s+', ' ', cmt.get_text().strip()).replace('"', '')
                if len(txt) > 10 and not txt.startswith('==') and not txt.startswith('⚙️'):
                    if txt not in page_comments:
                        page_comments.append(txt)
            all_comments.extend(page_comments)
            print(f"    ✅ Page {current_page}: +{len(page_comments)} bình luận")
        
        if current_page >= max_pages: break

        try:
            next_button = None
            buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='javascript:ratingCmtList']")
            for btn in buttons:
                match = re.search(r'ratingCmtList\((\d+)\)', btn.get_attribute("href"))
                if match and int(match.group(1)) == current_page + 1:
                    next_button = btn
                    break
            
            if next_button:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3)
                current_page += 1
            else: break
        except: break
        
    return list(set(all_comments))

def crawl_dmx_xiaomi_update(mode=1):
    """
    mode 1: Chỉ cập nhật giá (Nhanh - Dùng cho LSTM)
    mode 2: Cập nhật giá + Bình luận (Sâu - Dùng cho PhoBERT)
    """
    driver = get_driver()
    try:
        url_main = "https://www.dienmayxanh.com/dien-thoai-xiaomi"
        print(f"🚀 Khởi động quét Xiaomi...")
        driver.get(url_main)
        time.sleep(5)

        # 1. Nhấn 'Xem thêm' load toàn bộ sản phẩm
        while True:
            try:
                view_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".view-more a, .btn-view-more"))
                )
                driver.execute_script("arguments[0].click();", view_more)
                time.sleep(2)
            except: break

        # 2. Parse danh sách ban đầu
        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.find_all("a", class_="main-contain")
        
        raw_list = []
        for item in items:
            try:
                link = "https://www.dienmayxanh.com" + item['href']
                name = item.find("p", class_="product-title").get_text(strip=True)
                price_text = item.find("strong", class_="price").get_text(strip=True)
                img_tag = item.find("img")
                img_url = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
                if img_url.startswith("//"): img_url = "https:" + img_url

                raw_list.append({
                    "name": name, "price_display": price_text, 
                    "price_number": clean_price(price_text), "url": link, "image": img_url
                })
            except: continue

        # --- LỌC TRÙNG SẢN PHẨM TRONG LIST ---
        product_dict = {p['url']: p for p in raw_list}
        product_list = list(product_dict.values())
        print(f"📦 Tìm thấy {len(product_list)} sản phẩm Xiaomi độc nhất.")

        # 3. Duyệt từng sản phẩm để cập nhật DB
        today = datetime.now().strftime("%Y-%m-%d")

        for idx, p in enumerate(product_list, 1):
            try:
                print(f"\n📱 [{idx}/{len(product_list)}] Xử lý: {p['name']}")
                
                # A. KIỂM TRA CHỐNG LẶP GIÁ TRONG NGÀY
                existing_p = collection.find_one({"url": p["url"]})
                can_push_price = True
                if existing_p and "price_history" in existing_p:
                    # Lấy các ngày đã ghi nhận giá
                    recorded_dates = [h['date'] for h in existing_p["price_history"]]
                    if today in recorded_dates:
                        can_push_price = False

                # B. LẤY BÌNH LUẬN NẾU CHỌN MODE 2
                all_comments = []
                if mode == 2:
                    review_url = p['url'].rstrip('/') + "/danh-gia"
                    all_comments = get_all_comments_by_clicking(driver, review_url)

                # C. XÂY DỰNG QUERY UPDATE
                update_data = {
                    "$set": {
                        "name": p["name"],
                        "price_display": p["price_display"],
                        "price_number": p["price_number"],
                        "image": p["image"],
                        "last_updated": datetime.now(),
                        "last_crawl_date": today
                    }
                }

                # Chống lặp bình luận nội dung cũ
                if all_comments:
                    update_data["$addToSet"] = {"comments": {"$each": all_comments}}
                    update_data["$set"]["total_comments"] = len(all_comments)

                # Chỉ lưu giá nếu hôm nay chưa lưu (Để train LSTM chính xác)
                if can_push_price:
                    update_data["$push"] = {
                        "price_history": {"date": today, "price": p["price_number"]}
                    }
                    print(f"  📈 Đã thêm mốc giá mới cho ngày {today}")
                else:
                    print(f"  ✅ Giá ngày hôm nay đã tồn tại, bỏ qua.")

                # Thực thi MongoDB
                collection.update_one({"url": p["url"]}, update_data, upsert=True)
                
                if mode == 1:
                    print(f"  ✅ Cập nhật nhanh: {p['price_display']}")
                else:
                    time.sleep(2) # Nghỉ để tránh captcha

            except Exception as e:
                print(f"❌ Lỗi tại sản phẩm {p['name']}: {e}")

    finally:
        print("\n🏁 HOÀN TẤT CẬP NHẬT XIAOMI!")
        driver.quit()

if __name__ == "__main__":
    print("="*60)
    print("   HỆ THỐNG CRAWL DỮ LIỆU XIAOMI - DIỆN MÁY XANH")
    print("="*60)
    print("1. Chế độ NHANH (Chỉ cập nhật Giá - Train LSTM hàng ngày)")
    print("2. Chế độ ĐẦY ĐỦ (Cập nhật Giá + Bình luận - Train PhoBERT)")
    print("-" * 60)
    
    choice = input("Vui lòng chọn chế độ (1 hoặc 2): ")
    selected_mode = 2 if choice == '2' else 1
    
    crawl_dmx_xiaomi_update(mode=selected_mode)