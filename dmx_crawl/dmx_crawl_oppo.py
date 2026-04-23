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
collection = db["oppo_products"]

def get_driver():
    import tempfile
    import shutil
    
    chrome_options = Options()
    
    # Tạo thư mục profile tạm riêng để tránh xung đột file
    temp_profile_dir = os.path.join(tempfile.gettempdir(), "chrome_selenium_profile")
    if os.path.exists(temp_profile_dir):
        try:
            shutil.rmtree(temp_profile_dir)
        except:
            pass
    os.makedirs(temp_profile_dir, exist_ok=True)
    
    # Các arguments cần thiết để tránh lỗi session not created
    chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    
    # Experimental options
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # Sử dụng ChromeDriver - để tự động tải version phù hợp
    # Hoặc chỉ định đường dẫn thủ công nếu cần
    chromedriver_path = ChromeDriverManager().install()
    driver = webdriver.Chrome(
        service=Service(chromedriver_path),
        options=chrome_options
    )
    
    # Ẩn webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def clean_price(price_str):
    """Chuyển chuỗi giá '15.990.000₫' thành số nguyên 15990000"""
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def get_all_comments_by_clicking(driver, review_url):
    """Lấy bình luận từ tối đa 10 trang bằng cách nhấn nút Next"""
    all_comments = []
    current_page = 1
    max_pages = 10
    
    print(f"  🌐 Mở trang đánh giá: {review_url}")
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
                # Lọc bỏ các text quá ngắn hoặc ký tự rác
                if len(txt) > 10 and not txt.startswith('==') and not txt.startswith('⚙️'):
                    if txt not in page_comments:
                        page_comments.append(txt)
            all_comments.extend(page_comments)
            print(f"    ✅ Page {current_page}: Lấy được {len(page_comments)} bình luận")
        
        if current_page >= max_pages: break

        try:
            # Tìm nút Next trang tiếp theo (JS function của DMX)
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
        
    # Loại bỏ trùng lặp tuyệt đối
    return list(set(all_comments))

def crawl_dmx_oppo_update(mode=1):
    """
    mode 1: Chỉ cập nhật giá nhanh (LSTM)
    mode 2: Cập nhật giá + Bình luận sâu (PhoBERT)
    """
    driver = get_driver()
    try:
        url_main = "https://www.dienmayxanh.com/dien-thoai-oppo"
        print(f"🚀 Khởi động trình duyệt quét OPPO...")
        driver.get(url_main)
        time.sleep(5)

        # 1. Nhấn 'Xem thêm' để load toàn bộ danh sách
        while True:
            try:
                view_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".view-more a, .btn-view-more"))
                )
                driver.execute_script("arguments[0].click();", view_more)
                time.sleep(2)
            except: break

        # 2. Parse danh sách sản phẩm ban đầu
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

        # --- CHỐNG LẶP SẢN PHẨM TRONG LIST (Dùng URL làm khóa Duy nhất) ---
        product_dict = {p['url']: p for p in raw_list}
        product_list = list(product_dict.values())
        print(f"📦 Tìm thấy {len(product_list)} sản phẩm OPPO.")

        # 3. Duyệt từng sản phẩm để lưu Database
        today = datetime.now().strftime("%Y-%m-%d")

        for idx, p in enumerate(product_list, 1):
            try:
                print(f"\n📱 [{idx}/{len(product_list)}] Xử lý: {p['name']}")
                
                # A. Kiểm tra chống lặp giá trong cùng một ngày
                existing_p = collection.find_one({"url": p["url"]})
                can_push_price = True
                if existing_p and "price_history" in existing_p:
                    recorded_dates = [h['date'] for h in existing_p["price_history"]]
                    if today in recorded_dates:
                        can_push_price = False # Hôm nay có giá rồi, không push nữa

                # B. Lấy bình luận nếu chọn Mode 2
                all_comments = []
                if mode == 2:
                    review_url = p['url'].rstrip('/') + "/danh-gia"
                    all_comments = get_all_comments_by_clicking(driver, review_url)

                # C. Xây dựng Query cập nhật MongoDB
                update_query = {
                    "$set": {
                        "name": p["name"],
                        "price_display": p["price_display"],
                        "price_number": p["price_number"],
                        "image": p["image"],
                        "last_updated": datetime.now(),
                        "last_crawl_date": today
                    }
                }

                # Chống lặp bình luận bằng $addToSet
                if all_comments:
                    update_query["$addToSet"] = {"comments": {"$each": all_comments}}
                    update_query["$set"]["total_comments"] = len(all_comments)

                # Chống lặp lịch sử giá (Chỉ push nếu khác ngày)
                if can_push_price:
                    update_query["$push"] = {
                        "price_history": {"date": today, "price": p["price_number"]}
                    }
                    print(f"  📈 Đã thêm mốc giá mới cho ngày {today}")
                else:
                    print(f"  ✅ Giá ngày hôm nay đã tồn tại, không lưu trùng.")

                # Thực thi Update vào MongoDB
                collection.update_one({"url": p["url"]}, update_query, upsert=True)
                
                if mode == 1:
                    print(f"  ✅ Cập nhật nhanh: {p['price_display']}")
                else:
                    time.sleep(2) # Nghỉ ngắn tránh bị Web chặn

            except Exception as e:
                print(f"❌ Lỗi xử lý sản phẩm {p['name']}: {e}")

    except Exception as e:
        print(f"❌ Lỗi hệ thống chính: {e}")
    finally:
        print("\n" + "="*50)
        print("🏁 HOÀN TẤT CẬP NHẬT OPPO!")
        driver.quit()

if __name__ == "__main__":
    print("="*60)
    print("   HỆ THỐNG CRAWL DỮ LIỆU OPPO - ĐIỆN MÁY XANH")
    print("="*60)
    print("1. Chế độ NHANH (Chỉ cập nhật Giá - Phù hợp train LSTM hàng ngày)")
    print("2. Chế độ ĐẦY ĐỦ (Cập nhật Giá + Bình luận - Phù hợp train PhoBERT)")
    print("-" * 60)
    
    choice = input("Vui lòng chọn chế độ (1 hoặc 2): ")
    selected_mode = 2 if choice == '2' else 1
    
    crawl_dmx_oppo_update(mode=selected_mode)