# Hệ Thống So Sánh Giá Điện Thoại - AI Price Comparison

Hệ thống thu thập, so sánh giá sản phẩm điện thoại từ nền tảng thương mại điện tử lớn tại Việt Nam (FPT Shop, Thế Giới Di Động, Điện Máy Xanh) tích hợp phân tích cảm xúc và dự báo xu hướng giá sử dụng AI.

## 🎯 Tính Năng Chính

### 1. Thu Thập Dữ Liệu (Data Crawling)
- **Crawl tự động** từ 3 sàn TMĐT: FPT Shop, TGDĐ, ĐMX
- **Cập nhật giá** theo thời gian thực với lịch sử giá
- **Thu thập bình luận** từ người dùng
- Lưu trữ trong MongoDB với cấu trúc `price_history`

### 2. Search Fallback Engine 🔍
- **Xử lý khi không có dữ liệu sản phẩm** trong database (Theo góp ý giảng viên)
- Trả về thông báo + **gợi ý sản phẩm tương tự** cùng brand

### 3. Product Quality Score (PQS) ⭐
- **Thang điểm 100** đánh giá chất lượng tổng hợp:
  - Rating trung bình: 25%
  - Sentiment Score (PhoBERT): 30%
  - Uy tín gian hàng: 15%
  - Số lượng bán: 15%
  - Tỷ lệ phản hồi tích cực: 15%
- Phân loại: 🟢 Rất tốt (85+), 🟡 Tốt (70+), 🟠 Trung bình (50+), 🔴 Kém (<50)

### 4. Thống Kê Giá Toàn Diện 📊
- **Giá thấp nhất** (Min Price)
- **Giá trung bình** (Average Price)
- **Giá cao nhất** (Max Price)
- **Giá hiện tại** (Current Price)
- **Giá dự báo** (Forecast Price)
- So sánh giá hiện tại với mức trung bình để đưa ra khuyến nghị

### 5. Phân Tích Cảm Xúc (Sentiment Analysis)
- Model **PhoBERT** fine-tuned với 3 nhãn: Tích cực (+), Tiêu cực (-), Trung tính
- Phân tích khía cạnh (Aspect Classification): Camera, Pin, Màn hình, Giá, Hiệu năng...
- **Rule-based sentiment** kết hợp với AI để độ chính xác cao
- **Dashboard Sentiment Analytics** với biểu đồ tròn tỷ lệ cảm xúc
- **Review Quality Score (RQS)** đánh giá từng bình luận (thang 5) dựa trên sentiment + độ dài bình luận

### 6. Dự Báo Xu Hướng Giá (Price Forecasting)
- Model **LSTM (Long Short-Term Memory)** dự báo giá ngày tiếp theo
- Dựa trên lịch sử giá 5-7 ngày gần nhất
- **Xác định ranh giới tăng/giảm giá**: Giảm mạnh (≥5%), Giảm nhẹ (1-5%), Ổn định (±1%), Tăng nhẹ (1-5%), Tăng mạnh (≥5%)
- **Đánh giá độ chính xác LSTM**: MAE, RMSE, MAPE, Direction Accuracy (Tỷ lệ dự báo đúng hướng)

### 7. Buy Recommendation Engine 🛒
- **Nên mua ngay**: Giá thấp hơn trung bình ≥5% + PQS cao + Dự báo tăng
- **Nên mua**: Giá hiện tại thấp hơn giá trung bình
- **Nên chờ**: Dự báo giá giảm
- **Cân nhắc**: Giá cao hơn mức trung bình
- **Không khuyến nghị**: PQS < 50

### 8. So Sánh Đa Nền Tảng
- Hiển thị sản phẩm cùng model từ các sàn khác nhau
- Đối chiếu giá, đánh giá, dự báo
- Giao diện trực quan với Tailwind CSS

## 🏗️ Kiến Trúc Hệ Thống

```
ecommerce-price-comparison/
├── backend/
│   ├── main.py                    # FastAPI Backend
│   ├── models/                    # LSTM Models & Scalers
│   │   ├── *_lstm_best.keras
│   │   └── *_scaler.pkl
│   └── phobert_models/            # PhoBERT Models
│       ├── sentiment_classification/
│       └── aspect_classification/
├── frontend/
│   ├── index.html                 # Web Interface
│   └── logos/                     # Logo các sàn
├── tgdd_crawl/                    # Crawlers Thế Giới Di Động
├── fpt_crawl/                     # Crawlers FPT Shop
├── dmx_crawl/                     # Crawlers Điện Máy Xanh
├── data/                          # Datasets training
├── model/                         # Scripts train models
├── requirements.txt
├── start.bat / start.sh           # Scripts khởi động
└── scheduler.py                   # Tự động crawl định kỳ
```

## 🚀 Cài Đặt

### Yêu Cầu Hệ Thống
- Python 3.10+
- MongoDB 6.0+
- Chrome Browser

### Bước 1: Clone Repository
```bash
cd e:\ecommerce-price-comparison
```

### Bước 2: Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### Bước 3: Cấu Hình MongoDB
- Sử dụng MongoDB Atlas Cloud (connection string mặc định đã được cấu hình trong `.env.example`)
- Hoặc tải và cài đặt MongoDB Community Server

## 💻 Sử Dụng

### Khởi động nhanh (Windows)
```bash
start.bat
```

### Hoặc chạy thủ công

**1. Khởi động Backend (FastAPI):**
```bash
cd backend
python main.py
```
Server chạy tại: http://127.0.0.1:8000

**2. Khởi động Frontend:**
```bash
cd frontend
npx live-server --port=3000
```
Hoặc mở trực tiếp `index.html` trong trình duyệt

### Crawl Dữ Liệu Thủ Công

**Crawl FPT Shop:**
```bash
python fpt_crawl/fpt_crawl_ip.py      # iPhone
python fpt_crawl/fpt_crawl_ss.py      # Samsung
python fpt_crawl/fpt_crawl_oppo.py    # OPPO
python fpt_crawl/fpt_crawl_xiaomi.py  # Xiaomi
```

**Crawl Thế Giới Di Động:**
```bash
python tgdd_crawl/tgdd_crawl_ip.py      # iPhone
python tgdd_crawl/tgdd_crawl_ss.py      # Samsung
python tgdd_crawl/tgdd_crawl_oppo.py    # OPPO
python tgdd_crawl/tgdd_crawl_xiaomi.py  # Xiaomi
```

**Crawl Điện Máy Xanh:**
```bash
python dmx_crawl/dmx_crawl_ip.py      # iPhone
python dmx_crawl/dmx_crawl_ss.py      # Samsung
python dmx_crawl/dmx_crawl_oppo.py    # OPPO
python dmx_crawl/dmx_crawl_xiaomi.py  # Xiaomi
```

### Tự Động Crawl Định Kỳ
```bash
python scheduler.py
```
Script sẽ tự động crawl tất cả sàn mỗi 6 giờ.

## 📊 Training Models

### Train LSTM (Dự báo giá)
```bash
cd model
python train_lstm.py
```

### Train PhoBERT (Phân tích cảm xúc)
```bash
cd model
python train_phobert.py
```

## 🔍 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET | Search Fallback Engine - Kiểm tra sản phẩm tồn tại, trả về gợi ý nếu không có |
| `/api/compare` | GET | So sánh giá sản phẩm (PQS, Sentiment, LSTM Forecast, Buy Recommendation) |
| `/api/ingest` | POST | Ingest dữ liệu sản phẩm vào MongoDB |

**Ví dụ Request Search Fallback:**
```http
GET http://127.0.0.1:8000/api/search?brand=iphone&name=iPhone%2017
```

**Response khi không có dữ liệu:**
```json
{
  "found": false,
  "message": "Không tìm thấy sản phẩm 'iPhone 17' trong hệ thống.",
  "search_term": "iPhone 17",
  "suggestions": [
    {
      "platform": "FPT",
      "name": "iPhone 16 Pro Max 256GB",
      "current_price": 34990000,
      "image": "...",
      "link": "..."
    }
  ]
}
```

**Ví dụ Request:**
```http
GET http://127.0.0.1:8000/api/compare?brand=iphone&name=iPhone%2016%20Pro%20Max
```

**Response:**
```json
{
  "results": [
    {
      "platform": "FPT",
      "name": "iPhone 16 Pro Max",
      "current_price": 34990000,
      "forecast": 34500000,
      "sentiment": {
        "pos": 75,
        "neu": 15,
        "neg": 10,
        "list": [...]
      },
      "chart": {
        "labels": ["10/04", "11/04", "12/04"],
        "data": [34990000, 34990000, 34990000]
      }
    }
  ]
}
```

## 🧠 Công Nghệ Sử Dụng

| Công Nghệ | Mục Đích |
|-----------|----------|
| **FastAPI** | Backend API |
| **MongoDB** | Database |
| **Selenium** | Web Scraping |
| **PhoBERT** | NLP Sentiment Analysis |
| **LSTM** | Time Series Forecasting |
| **Tailwind CSS** | UI Styling |
| **Chart.js** | Data Visualization |

## 📁 Cấu Trúc Database

**Database:** `price_tracker` (MongoDB Atlas)

**Collections:**
- `{brand}_full_data` - Dữ liệu FPT Shop
- `{brand}_master_data` - Dữ liệu TGDĐ
- `{brand}_products` - Dữ liệu ĐMX

**Document Structure:**
```javascript
{
  "_id": ObjectId,
  "name": "iPhone 15 Pro Max 256GB",
  "price_number": 32990000,
  "price_display": "32.990.000đ",
  "url": "...",
  "image": "...",
  "price_history": [
    {"date": "2026-04-12", "price": 32990000},
    {"date": "2026-04-11", "price": 32990000}
  ],
  "comments": ["Sản phẩm tốt", "Đáng mua"],
  "last_crawl_date": "2026-04-12"
}
```

## 🔧 Cấu Hình

### Backend `backend/main.py`
- `LOOK_BACK = 5` - Số ngày dùng để dự báo LSTM
- `BRANDS = ["iphone", "samsung", "oppo", "xiaomi"]` - Các hãng hỗ trợ
- MongoDB URI: `mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham`
- MongoDB DB: `price_tracker`

### Frontend `frontend/index.html`
- API URL: `http://127.0.0.1:8000/api/compare`
- Logo path: `./logos/`

## 🐛 Xử Lý Lỗi Thường Gặp

**1. Lỗi kết nối MongoDB:**
```bash
# Kiểm tra kết nối tới MongoDB Atlas
mongosh "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"

# Đảm bảo IP của bạn được thêm vào Access List trong MongoDB Atlas
```

**2. Lỗi ChromeDriver:**
```bash
# Cập nhật webdriver-manager
pip install --upgrade webdriver-manager
```

**3. Lỗi load model PhoBERT:**
- Kiểm tra path model trong `main.py`
- Đảm bảo models đã được train

## 👨‍💻 Tác Giả

- Phát triển bởi: An Nguyễn
- Trường: Đại học Bình Dương (BDU)
- Lĩnh vực: AI, Web Scraping, Data Science

## 📄 License

MIT License - Free to use and modify.

---

**⚠️ Lưu ý:** 
- Hệ thống chỉ sử dụng cho mục đích học tập và nghiên cứu
- Tuân thủ robots.txt của các website crawl
- Không crawl quá nhanh để tránh bị chặn IP
