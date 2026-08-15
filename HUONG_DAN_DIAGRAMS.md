# Hướng Dẫn Sử Dụng Files Diagram

## 📁 Danh Sách Files Đã Tạo

### 1. **Chuong3_PhanTichThietKe.docx**
- File Word chính chứa nội dung chương 3 viết lại
- Bao gồm: yêu cầu chức năng, phi chức năng, kiến trúc, mô hình AI
- Sẵn sàng để in và trình bày

### 2. **diagrams_uml.md**
- Các sơ đồ UML ở định dạng text/ASCII art
- Có thể xem trực tiếp trong editor
- Bao gồm 10 hình chính

### 3. **diagrams/ folder** - Các file PlantUML
- `context.puml` - Sơ đồ ngữ cảnh
- `usecase.puml` - Sơ đồ use case
- `architecture.puml` - Sơ đồ kiến trúc phân tầng
- `sequence_search.puml` - Sơ đồ tuần tự tìm kiếm
- `sequence_crawl.puml` - Sơ đồ tuần tự crawl dữ liệu
- `sequence_sentiment.puml` - Sơ đồ tuần tự phân tích cảm xúc
- `sequence_forecast.puml` - Sơ đồ tuần tự dự báo giá
- `data_model.puml` - Sơ đồ cấu trúc dữ liệu MongoDB (Data Model Diagram)

---

## 🔄 Cách Chuyển Đổi PlantUML Thành Hình Ảnh

### Phương Pháp 1: Sử dụng PlantUML Online (Nhanh nhất)
1. Truy cập: https://www.plantuml.com/plantuml/uml/
2. Copy nội dung từ file `.puml`
3. Paste vào editor trên trang web
4. Export thành PNG hoặc SVG

### Phương Pháp 2: Sử dụng Command Line (Local)
```bash
# Cài đặt PlantUML
pip install plantuml

# Chuyển đổi file
plantuml diagrams/context.puml -o diagrams/images -tpng

# Hoặc nếu dùng Java
java -jar plantuml.jar diagrams/context.puml -o ../images/ -tpng
```

### Phương Pháp 3: Sử dụng VS Code Extension
1. Cài đặt extension: "PlantUML" (Jebbs)
2. Right-click trên file `.puml` → Preview
3. Click "Export" để lưu ảnh

### Phương Pháp 4: Sử dụng Script Python (Tự động)
```python
# Chạy convert_diagrams.py (nếu có)
python convert_diagrams.py
```

---

## 📋 Cách Thêm Hình Ảnh Vào File Word

### Cách 1: Chỉnh Sửa Thủ Công
1. Mở `Chuong3_PhanTichThietKe.docx` trong Microsoft Word
2. Tìm phần "[Hình 3-X: ... - Xem phụ lục]"
3. Right-click → Insert Picture
4. Chọn file PNG/SVG tương ứng
5. Điều chỉnh kích thước và caption
6. Lưu file

### Cách 2: Sử dụng Script Python Tự Động
```bash
python update_word_with_diagrams.py
```

---

## 🎯 Các Hình Vẽ Chi Tiết

### Hình 3-1: Sơ Đồ Ngữ Cảnh (Context Diagram)
**File:** `diagrams/context.puml`
- Hiển thị tương tác giữa User, Smart Shopping Assistant, và 8 sàn TMĐT
- Database MongoDB ở trung tâm
- Flow: Input → System → Output

### Hình 3-2: Sơ Đồ Use Case
**File:** `diagrams/usecase.puml`
- 7 use cases cho End User
- 3 use cases cho System
- Quan hệ include/extend giữa các use case

### Hình 3-3: Sơ Đồ Kiến Trúc Hệ Thống
**File:** `diagrams/architecture.puml`
- 3 tầng: Presentation, Application, Data
- Chi tiết từng component
- Luồng kết nối giữa các tầng

### Hình 3-4: Sơ Đồ Cấu Trúc Dữ Liệu MongoDB (Data Model Diagram)
**File:** `diagrams/data_model.puml`
- 7 collections chính
- Mô tả schema (cấu trúc) của từng collection
- Thuộc tính của mỗi collection
- Không dùng quan hệ ER (MongoDB là NoSQL)

### Hình 3-5-9: Sơ Đồ Tuần Tự (Sequence Diagrams)
**Files:**
- `sequence_search.puml` - Quy trình tìm kiếm
- `sequence_crawl.puml` - Quy trình crawl dữ liệu
- `sequence_sentiment.puml` - Quy trình phân tích cảm xúc
- `sequence_forecast.puml` - Quy trình dự báo giá

---

## 💡 Mẹo Và Lưu Ý

### Nếu PlantUML Không Cài Được
- Sử dụng PlantUML Online (https://www.plantuml.com/plantuml/uml/)
- Hoặc dùng draw.io để vẽ lại theo mô tả

### Để Cải Thiện Chất Lượng Hình
1. Export dưới dạng SVG thay vì PNG (vector graphics)
2. Chỉnh resolution cao hơn: `-Djava.awt.headless=true`
3. Sử dụng theme custom nếu cần

### Để Sửa Diagram
1. Mở file `.puml` bằng text editor
2. Sửa code theo cú pháp PlantUML
3. Re-export thành ảnh

### Files Cần Nhất
- ✅ `Chuong3_PhanTichThietKe.docx` - Chương 3 chính
- ✅ `diagrams_uml.md` - Sơ đồ text (backup)
- ✅ `diagrams/*.puml` - Sơ đồ chi tiết (để export)

---

## 🚀 Next Steps

1. **Chuyển đổi PlantUML → PNG/SVG:**
   ```bash
   cd diagrams
   # Dùng online hoặc script
   ```

2. **Thêm hình vào Word:**
   - Mở file Word
   - Insert → Picture
   - Chọn từ folder images/

3. **Kiểm tra lại nội dung:**
   - Số hình khớp với tham chiếu (3-1 đến 3-9)
   - Tên hình rõ ràng
   - Format consistent

4. **Gửi báo cáo:**
   - File Word final
   - Kèm folder diagrams (nếu cần)

---

## 📞 Hỗ Trợ

- Nếu gặp lỗi PlantUML → Dùng PlantUML Online
- Nếu không thấy hình → Check file path và format
- Nếu cần sửa nội dung → Edit file `.puml` hoặc `.md` rồi regenerate

---

**Tạo lúc:** 2026-08-13  
**Version:** 1.0  
**Status:** ✅ Ready to use

