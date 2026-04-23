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

# --- KHẮC PHỤC LỖI PROXY ---
for key in ["http_proxy", "https_proxy", "no_proxy"]:
    if key in os.environ: del os.environ[key]

# --- KẾT NỐI MONGODB ---
client = MongoClient("mongodb://localhost:27017/")
db = client["dmx_database"]
collection = db["iphone_products"]

def     get_driver():
    chrome_options = Options()
    # KHÔNG dùng headless - hiển thị cửa sổ để quan sát
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    chrome_options.add_argument('--proxy-server="direct://"')
    chrome_options.add_argument('--proxy-bypass-list=*')
    chrome_options.add_argument("--start-maximized")  # Mở cửa sổ to để dễ quan sát
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def clean_price(price_str):
    """Chuyển đổi '29.990.000₫' thành 29990000 để train LSTM"""
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def get_all_comments_by_clicking(driver, review_url):
    """Lấy tất cả bình luận bằng cách nhấn nút mũi tên để chuyển trang, tối đa 10 trang"""
    all_comments = []
    current_page = 1
    max_pages = 10
    
    print(f"  🌐 Đang mở trang đánh giá: {review_url}")
    driver.get(review_url)
    time.sleep(4)
    
    while current_page <= max_pages:
        print(f"\n  {'='*50}")
        print(f"  📄 Đang xử lý PAGE {current_page}/{max_pages}")
        
        # Cuộn để tải nội dung trang hiện tại
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Parse HTML để lấy bình luận
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Tìm tất cả bình luận với selector p.cmt-txt
        cmt_elements = soup.select("p.cmt-txt")
        
        if not cmt_elements:
            # Thử selector dự phòng
            cmt_elements = soup.select(".cmt-txt, .comment-text, .review-text")
        
        if cmt_elements:
            # Lấy bình luận từ trang hiện tại
            page_comments = []
            for cmt in cmt_elements:
                txt = cmt.get_text().strip()
                # Làm sạch text
                txt = re.sub(r'\s+', ' ', txt)
                txt = txt.replace('"', '').strip()
                
                # Chỉ lấy bình luận có nội dung có ý nghĩa
                if len(txt) > 10 and not txt.startswith('==') and not txt.startswith('⚙️'):
                    if txt not in page_comments:
                        page_comments.append(txt)
            
            if page_comments:
                all_comments.extend(page_comments)
                print(f"  ✅ Page {current_page}: Lấy được {len(page_comments)} bình luận")
                print(f"  📊 Tổng số bình luận hiện tại: {len(all_comments)}")
                
                # Hiển thị 2 bình luận đầu trang để kiểm tra
                for i, cmt in enumerate(page_comments[:2], 1):
                    preview = cmt[:80] + "..." if len(cmt) > 80 else cmt
                    print(f"     📝 Ví dụ {i}: {preview}")
            else:
                print(f"  ⚠️ Không có bình luận hợp lệ ở page {current_page}")
        else:
            print(f"  ⚠️ Không tìm thấy phần tử bình luận ở page {current_page}")
        
        # Nếu đã đạt giới hạn 10 trang thì dừng
        if current_page >= max_pages:
            print(f"  🛑 Đã đạt giới hạn {max_pages} trang, dừng lại")
            break
        
        # Tìm và nhấn nút next (mũi tên) để sang trang tiếp theo
        try:
            # Tìm nút next với javascript:ratingCmtList
            next_button = None
            
            # Cách 1: Tìm bằng href chứa javascript:ratingCmtList
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='javascript:ratingCmtList']")
                for btn in buttons:
                    href = btn.get_attribute("href")
                    # Lấy số trang từ href
                    match = re.search(r'ratingCmtList\((\d+)\)', href)
                    if match:
                        page_num = int(match.group(1))
                        if page_num == current_page + 1:
                            next_button = btn
                            print(f"  🔍 Tìm thấy nút next với href: {href}")
                            break
            except:
                pass
            
            # Cách 2: Tìm nút có nội dung là › hoặc >
            if not next_button:
                try:
                    # Tìm tất cả các link có chứa ký tự mũi tên
                    arrows = driver.find_elements(By.XPATH, "//a[contains(text(), '›') or contains(text(), '>') or contains(text(), '→')]")
                    for arrow in arrows:
                        # Kiểm tra xem có phải nút next không
                        if arrow.is_displayed() and arrow.is_enabled():
                            next_button = arrow
                            print(f"  🔍 Tìm thấy nút next với text: {arrow.text}")
                            break
                except:
                    pass
            
            # Cách 3: Tìm nút next bằng class
            if not next_button:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, ".pagination .next a, .pagination a.next, .next-page")
                    print(f"  🔍 Tìm thấy nút next bằng class selector")
                except:
                    pass
            
            if next_button and next_button.is_enabled():
                # Cuộn đến nút next
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1)
                
                # Nhấn nút next
                print(f"  🔄 Đang nhấn nút next để chuyển sang page {current_page + 1}...")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3)  # Chờ trang mới load
                
                current_page += 1
            else:
                print(f"  🏁 Không tìm thấy nút next hoặc nút đã disabled, đã hết trang")
                break
                
        except Exception as e:
            print(f"  🏁 Không thể chuyển sang trang tiếp theo: {e}")
            break
    
    # Loại bỏ trùng lặp
    unique_comments = []
    for cmt in all_comments:
        if cmt not in unique_comments and len(cmt) > 10:
            unique_comments.append(cmt)
    
    print(f"\n  {'='*50}")
    print(f"  📊 TỔNG KẾT: Đã lấy {len(unique_comments)} bình luận độc nhất từ {current_page} trang")
    return unique_comments

# ... (Giữ nguyên các phần import và hàm get_driver, clean_price, get_all_comments_by_clicking phía trên)

def crawl_dmx_iphone_update_price(mode=1):
    """
    mode 1: Chỉ cào thông tin sản phẩm & Giá (Nhanh)
    mode 2: Cào Giá + Toàn bộ bình luận (Chậm hơn)
    """
    driver = get_driver()
    try:
        url_main = "https://www.dienmayxanh.com/dien-thoai-apple-iphone"
        print(f"\n🚀 Bắt đầu quét danh sách iPhone từ: {url_main}")
        driver.get(url_main)
        time.sleep(5)

        # --- PHẦN 1: QUÉT DANH SÁCH SẢN PHẨM ---
        click_count = 0
        while True:
            try:
                view_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".view-more a, .btn-view-more, a.view-more-btn"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", view_more)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", view_more)
                click_count += 1
                print(f"  🔄 Đã nhấn 'Xem thêm' lần thứ {click_count}")
                time.sleep(2)
            except:
                print(f"  ✅ Đã load xong toàn bộ danh sách sản phẩm")
                break

        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.find_all("a", class_="main-contain")
        
        product_list = []
        for item in items:
            try:
                link = "https://www.dienmayxanh.com" + item['href']
                name = item.find("p", class_="product-title").get_text(strip=True)
                price_text = item.find("strong", class_="price").get_text(strip=True)
                price_num = clean_price(price_text)
                img_tag = item.find("img")
                img_url = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
                if img_url and img_url.startswith("//"): img_url = "https:" + img_url

                product_list.append({
                    "name": name, "price_display": price_text,
                    "price_number": price_num, "url": link, "image": img_url
                })
            except: continue

        # --- PHẦN 2: CẬP NHẬT VÀO DATABASE ---
        print(f"\n--- Đang cập nhật {len(product_list)} sản phẩm vào MongoDB (Chế độ: {'Chỉ Giá' if mode==1 else 'Giá & Bình luận'}) ---")

        for idx, p in enumerate(product_list, 1):
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                update_data = {
                    "name": p["name"],
                    "price_display": p["price_display"],
                    "price_number": p["price_number"],
                    "image": p["image"],
                    "last_updated": datetime.now(),
                    "last_crawl_date": today
                }

                # LOGIC LỰA CHỌN: Nếu chọn mode 2 thì mới đi cào bình luận
                all_comments = []
                if mode == 2:
                    print(f"\n📱 [{idx}/{len(product_list)}] Đang cào bình luận cho: {p['name']}")
                    review_url = p['url'].rstrip('/') + "/danh-gia"
                    all_comments = get_all_comments_by_clicking(driver, review_url)
                    update_data["total_comments"] = len(all_comments)
                    update_data["review_url"] = review_url

                # THỰC HIỆN UPDATE MONGODB
                query = {"url": p["url"]}
                operation = {
                    "$set": update_data,
                    "$push": {
                        "price_history": {"date": today, "price": p["price_number"]}
                    }
                }
                
                # Nếu có bình luận thì mới dùng $addToSet
                if all_comments:
                    operation["$addToSet"] = {"comments": {"$each": all_comments}}

                collection.update_one(query, operation, upsert=True)
                
                if mode == 1:
                    print(f"  ✅ [{idx}/{len(product_list)}] {p['name']}: {p['price_display']} (Đã lưu)")
                else:
                    print(f"  💾 Đã lưu xong {p['name']} kèm {len(all_comments)} bình luận")

            except Exception as e:
                print(f"❌ Lỗi tại sản phẩm {idx}: {e}")

    finally:
        driver.quit()
        print("\n👋 Đã hoàn tất và đóng trình duyệt!")

if __name__ == "__main__":
    print("="*50)
    print("   CÔNG CỤ CÀO DỮ LIỆU IPHONE - ĐIỆN MÁY XANH")
    print("="*50)
    print("1. Chỉ cào Tên & Giá (Rất nhanh)")
    print("2. Cào Giá & Toàn bộ Bình luận (Chậm - Cần mở từng SP)")
    print("-"*50)
    
    choice = input("Vui lòng chọn chế độ (1 hoặc 2): ")
    
    if choice == '1':
        crawl_dmx_iphone_update_price(mode=1)
    elif choice == '2':
        crawl_dmx_iphone_update_price(mode=2)
    else:
        print("❌ Lựa chọn không hợp lệ. Thoát chương trình.")

if __name__ == "__main__":
    print("🌟 BẮT ĐẦU QUÉT DỮ LIỆU TỪ DIỆN MÁY XANH 🌟")
    print("⚠️ Cửa sổ trình duyệt sẽ hiện ra - ĐỪNG ĐÓNG!")
    print("⏳ Quá trình có thể mất vài phút...")
    print("="*70)
    crawl_dmx_iphone_update_price()