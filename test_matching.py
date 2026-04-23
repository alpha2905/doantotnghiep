import re

def clean_product_name(name):
    if not name: return ""
    name = name.lower()
    # Thay thế các từ viết tắt phổ biến
    name = name.replace("ip ", "iphone ")
    name = name.replace("ss ", "samsung ")
    name = name.replace("điện thoại", "").strip()
    return " ".join(name.split())

def extract_model_base(name):
    name = clean_product_name(name)
    # Loại bỏ các thông số kỹ thuật phổ biến để lấy model gốc
    # Ví dụ: "iphone 12 128gb" -> "iphone 12"
    # "samsung galaxy s21 ultra 5g" -> "samsung galaxy s21 ultra"
    
    # 1. Loại bỏ dung lượng (gb, tb)
    name = re.sub(r'\d+\s*(gb|tb)', '', name)
    
    # 2. Loại bỏ các từ bổ trợ không phải là model chính
    junk_words = ["chính hãng", "vn/a", "5g", "4g", "lte", "lắp sim", "hàng nhập khẩu"]
    for word in junk_words:
        name = name.replace(word, "")
    
    # 3. Làm sạch khoảng trắng thừa
    return " ".join(name.split())

test_cases = [
    "iPhone 12 128GB",
    "iPhone 12 Pro 256GB Chính hãng VN/A",
    "Điện thoại Samsung Galaxy S21 Ultra 5G",
    "ip 12",
    "ss s21",
    "iPhone 15 Pro Max 1TB"
]

print("--- Testing Name Extraction ---")
for tc in test_cases:
    cleaned = clean_product_name(tc)
    base = extract_model_base(tc)
    print(f"Original: {tc}")
    print(f"Cleaned:  {cleaned}")
    print(f"Base:     {base}")
    print("-" * 20)
