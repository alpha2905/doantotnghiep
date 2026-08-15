# Chương 3: Phân Tích và Thiết Kế Hệ Thống
## Các Sơ Đồ UML Cho Hệ Thống Smart Shopping Assistant

---

## Hình 3-1: Sơ Đồ Ngữ Cảnh (Context Diagram)

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                        SÀN THƯƠNG MẠI ĐIỆN TỬ                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐                 │
│  │  FPT Shop   │ │ Thế Giới     │ │ CellphoneS   │ │ Hoàng Hà    │                 │
│  │             │ │ Di Động      │ │              │ │ Mobile      │                 │
│  └──────┬──────┘ └──────┬───────┘ └──────┬───────┘ └──────┬──────┘                 │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐                 │
│  │Di Động Việt │ │Viettel Store │ │  Clickbuy    │ │ MobileCity  │                 │
│  └──────┬──────┘ └──────┬───────┘ └──────┬───────┘ └──────┬──────┘                 │
└─────────┼───────────────┼────────────────┼───────────────┼─────────────────────────┘
          │ Crawl: name,  │ Crawl: price,  │ Crawl: comments│ Crawl: URL, image
          │ price, URL    │ history        │               │
          ▼               ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│            HỆ THỐNG SO SÁNH GIÁ ĐIỆN THOẠI (AI PRICE COMPARISON)                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │ • Search & Filter                          (Web Interface - React)           │  │
│  │ • Price Comparison                          (Backend API - FastAPI)          │  │
│  │ • Real-time Data Crawling                   (Crawler Module)                 │  │
│  │ • Sentiment Analysis                        (PhoBERT)                        │  │
│  │ • Price Forecasting                         (LSTM)                           │  │
│  │ • Product Quality Score (PQS)               (AI Module)                      │  │
│  │ • Buy Recommendation                        (Recommendation Engine)          │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                              │
│                          ┌───────────▼───────────┐                                  │
│                          │      MongoDB          │                                  │
│                          └───────────────────────┘                                  │
└──────────────────────────────┬──────────────────────────────────────────────────────┘
                               │
                               │ Response: products, prices,
                               │ sentiment scores, forecasts,
                               │ PQS, recommendations
                               │
                    ┌──────────▼──────────┐
                    │  NGƯỜI DÙNG (User)   │
                    │ • Search products    │
                    │ • View comparisons   │
                    │ • See forecasts      │
                    │ • Get recommendations│
                    └─────────────────────┘
```

---

## Hình 3-2: Sơ Đồ Use Case Chính

```
┌──────────────────────────────────────────────────────────────────┐
│                  Smart Shopping Assistant System                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  UC1: Search Products                                   │   │
│  │  UC2: View Product Quality Score (PQS)                 │   │
│  │  UC3: View Price History & Chart                        │   │
│  │  UC4: View Sentiment Analysis                           │   │
│  │  UC5: View Price Forecast                               │   │
│  │  UC6: Get Buy Recommendation                            │   │
│  │  UC7: Compare Multi-Platform Prices                     │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  UC8: Crawl Data (System)                                │   │
│  │  UC9: Sentiment Analysis (System)                        │   │
│  │  UC10: Price Forecasting (System)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

       ┌─────────────────┐
       │  End User       │──── uses ──► UC1, UC2, UC3, UC4, UC5, UC6, UC7
       │ (Customer)      │
       └─────────────────┘

       ┌─────────────────┐
       │ System (Server) │──── executes ──► UC8, UC9, UC10
       └─────────────────┘
```

---

## Hình 3-3: Sơ Đồ Kiến Trúc Hệ Thống (Layered Architecture)

```
┌────────────────────────────────────────────────────────────────┐
│          PRESENTATION LAYER (Giao Diện)                        │
│  ┌─────────────────┐              ┌──────────────────┐        │
│  │  React.js Web   │              │  Flutter Mobile  │        │
│  │  • Search UI    │              │ (Future)         │        │
│  │  • Charts       │              │                  │        │
│  │  • Dashboard    │              │                  │        │
│  └────────┬────────┘              └──────────────────┘        │
│           │                                                    │
└───────────┼────────────────────────────────────────────────────┘
            │
     REST API + WebSocket
            │
┌───────────▼────────────────────────────────────────────────────┐
│      APPLICATION LAYER (Xử lý & Logic)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend Server                      │  │
│  │  • User Authentication (Firebase)                        │  │
│  │  • Product Search & Filtering                            │  │
│  │  • API Endpoints (/search, /products, /forecast, etc)   │  │
│  │  • Business Logic                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  Crawler       │  │  AI Module   │  │  Scheduler      │   │
│  │  Module        │  │              │  │ (APScheduler)   │   │
│  │                │  │ • PhoBERT    │  │                 │   │
│  │ • Playwright   │  │ • LSTM       │  │ • Periodic      │   │
│  │ • BeautifulSoup│  │              │  │   jobs          │   │
│  │ • 3 Crawlers   │  └──────────────┘  └─────────────────┘   │
│  │   (FPT, TGDĐ,  │                                           │
│  │    ĐMX)        │                                           │
│  └────────────────┘                                            │
└────────────┬──────────────────────────────────────────────────┘
             │
    Database Connection
             │
┌────────────▼──────────────────────────────────────────────────┐
│         DATA LAYER (Lưu Trữ Dữ Liệu)                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              MongoDB NoSQL Database                      │ │
│  │  • 8 collection sản phẩm theo sàn:                      │ │
│  │    fpt, tgdd, cellphones, hoangha,                      │ │
│  │    didongviet, viettelstore, clickbuy, mobilecity       │ │
│  │  • users collection (người dùng)                        │ │
│  │  • notifications collection (thông báo)                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │       Model Storage (Models & Weights)                   │ │
│  │  • LSTM .keras files + scalers.pkl                       │ │
│  │  • PhoBERT model weights                                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Hình 3-4: Sơ Đồ Cấu Trúc Dữ Liệu MongoDB (Data Model Diagram)

```
┌─────────────────────────────────────────────────────────────┐
│         CẤU TRÚC DỮ LIỆU MONGODB (NoSQL)                   │
│              DATABASE: price_tracker                        │
└─────────────────────────────────────────────────────────────┘

┌─── COLLECTION: fpt (FPT Shop) ──┐   ┌─── COLLECTION: tgdd (TGDĐ) ──┐
│ _id: ObjectId (PK)              │   │ _id: ObjectId (PK)           │
│ platform: String                │   │ platform: String             │
│ brand: String (iphone/samsung)  │   │ brand: String                │
│ name: String                    │   │ name: String                 │
│ model_base: String              │   │ model_base: String           │
│ price_number: Int               │   │ price_number: Int            │
│ price: String/Int (giá thô)     │   │ price: String/Int            │
│ image / image_url: String (URL) │   │ image / image_url: String    │
│ url / product_url: String (UK)  │   │ url / product_url: String    │
│ rating: Float (0-5)             │   │ rating: Float (0-5)          │
│ sold: Int                       │   │ sold: Int                    │
│ shop_reputation: Float (0-100)  │   │ shop_reputation: Float       │
│ comments: Array[String]         │   │ comments: Array[String]      │
│ price_history: Array[Object]    │   │ price_history: Array[Object] │
│   [{scraped_at, price}]         │   │   [{scraped_at, price}]      │
│ forecast: Int (LSTM)            │   │ forecast: Int (LSTM)         │
│ last_crawl: Date                │   │ last_crawl: Date             │
│ last_scraped_at: Date           │   │ last_scraped_at: Date        │
└─────────────────────────────────┘   └──────────────────────────────┘

┌─── COLLECTION: cellphones ──────┐   ┌─── COLLECTION: hoangha ──────┐
│ (CellphoneS) — cấu trúc giống   │   │ (Hoàng Hà Mobile) — cấu trúc │
│  như fpt/tgdd                   │   │  giống như fpt/tgdd           │
└─────────────────────────────────┘   └──────────────────────────────┘

┌─── COLLECTION: didongviet ──────┐   ┌─── COLLECTION: viettelstore ─┐
│ (Di Động Việt) — cấu trúc giống │   │ (Viettel Store) — cấu trúc   │
│  như fpt/tgdd                   │   │  giống như fpt/tgdd           │
└─────────────────────────────────┘   └──────────────────────────────┘

┌─── COLLECTION: clickbuy ────────┐   ┌─── COLLECTION: mobilecity ───┐
│ (Clickbuy) — cấu trúc giống     │   │ (MobileCity) — cấu trúc giống│
│  như fpt/tgdd                   │   │  như fpt/tgdd                 │
└─────────────────────────────────┘   └──────────────────────────────┘
        (8 collection sản phẩm — cấu trúc document giống nhau)

┌─── COLLECTION: users ───────────┐
│ _id: ObjectId (PK)              │
│ email: String (UK)              │
│ password_hash: String (bcrypt)  │
│ full_name: String               │
│ favorites: Array[Object]        │
│   [{platform, name,             │
│     current_price, forecast,    │
│     image, link, added_pqs,     │
│     added_at}]                  │
│ fcm_tokens: Array[String]       │
│ created_at: Date                │
└─────────────────────────────────┘

┌─── COLLECTION: notifications ───┐
│ _id: ObjectId (PK)              │
│ user_id: String (FK)            │
│ key: String (UK)                │
│ type: String                    │
│   (price_drop|deep_drop|        │
│    below_avg|forecast_up|       │
│    pqs_up|negative_comments)    │
│ title: String                   │
│ message: String                 │
│ product: Object                 │
│ created_at: Date                │
│ read: Boolean                   │
└─────────────────────────────────┘

Quan hệ: users 1 ─── N notifications (qua user_id)
```

---

## Hình 3-5: Kiến Trúc Mô Hình AI (AI Module Architecture)

**File:** `diagrams/ai_architecture.puml` — Xem hình ảnh: `diagrams/images/ai_architecture.png`

```
┌────────────────────────────────────────────────────────────────┐
│              AI MODULE ARCHITECTURE (Kiến Trúc Mô Hình AI)     │
└────────────────────────────────────────────────────────────────┘

Pipeline 1: PHÂN TÍCH CẢM XÚC & KHÍA CẠNH (PhoBERT)
Input: Comment Text (Tiếng Việt)
   │
   ▼
Text Preprocessing
   • Remove punctuation
   • Lowercase
   • Normalize
   │
   ▼
Tokenization (PhoBERT Tokenizer)
   │
   ▼
Embedding (PhoBERT-base-v2)
   │
   ├──────────────────────────────┐
   ▼                              ▼
Sentiment Model               Aspect Model
(3 labels)                    (10 labels)
  - positive                   - bảo_mật  - camera
  - neutral                    - giá      - hiệu_năng
  - negative                   - hệ_điều_hành - khác
                               - loa_âm_thanh - màn_hình
                               - pin      - thiết_kế
   │                              │
   └──────────────┬───────────────┘
                  ▼
Rule-based (ưu tiên cao)
   • Sentiment keywords (strong_negative,
     positive_words, question_words)
   • Aspect keywords (từ điển keyword → aspect)
   └ Nếu không khớp rule → dùng kết quả PhoBERT
                  │
                  ▼
Output: Sentiment % (pos/neu/neg) + Aspects + RQS Score


Pipeline 2: DỰ BÁO GIÁ (LSTM - Model Tổng Quát)
Input: Price History (6-7 ngày) từ MongoDB
   │
   ▼
Data Cleaning
   • Lọc giá trị hợp lệ (price_value / price string)
   • Gom giá theo ngày (scraped_at → date)
   • Giữ giá cuối cùng trong ngày
   │
   ▼
Normalization (MinMaxScaler - fit trên toàn bộ giá)
   │
   ▼
Sequence Preparation (LOOK_BACK = 5)
   • X = prices[i : i+5]
   • y = prices[i+5]
   │
   ▼
LSTM Model (Tổng quát - 1 model duy nhất)
   • LSTM(64, return_sequences=True)
   • Dropout(0.2)
   • LSTM(32)
   • Dense(1)
   • Loss: MSE | Optimizer: Adam
   │
   ▼
Inverse Scaling (denormalize về giá thực)
   │
   ▼
Output: Forecast Price + Trend + Metrics
   • MAE, RMSE, MAPE, Direction Accuracy
   • Trend: Giảm mạnh / Giảm nhẹ / Ổn định / Tăng nhẹ / Tăng mạnh


PQS CALCULATOR (Product Quality Score - Thang 100)
   • Rating trung bình (0-5) → 25%
   • Sentiment Score (% tích cực) → 30%
   • Uy tín gian hàng (shop_reputation) → 15%
   • Số lượng bán (sold, chuẩn hóa /1000) → 15%
   • Tỷ lệ phản hồi tích cực → 15%
                              │
                              ▼
                        PQS (0-100)
                        + Nhãn chất lượng
                        (🟢 Rất tốt / 🟡 Tốt /
                         🟠 Trung bình / 🔴 Kém)


Pipeline 3: RECOMMENDATION ENGINE (Khuyến Nghị Mua)
Input: PQS + Price Stats (Min/Avg/Max/Current) + Forecast
   │
   ▼
Logic quyết định mua
   IF (PQS < 50)                    → "Không khuyến nghị" ⛔
   IF (giá thấp hơn TB ≥5% + forecast tăng) → "Nên mua ngay" ✅
   IF (giá thấp hơn TB)             → "Nên mua" 🛒
   IF (forecast giảm)               → "Nên chờ" ⏳
   ELSE                             → "Cân nhắc" 🤔
   │
   ▼
Output: Khuyến nghị mua + Lý do chi tiết
```

---

## Hình 3-6: Sơ Đồ Tuần Tự - Use Case Tìm Kiếm Sản Phẩm

```
User            Frontend (React)     Backend (FastAPI)    Database (MongoDB)
│                   │                      │                      │
├─ Enter search ───►│                      │                      │
│  product name     │                      │                      │
│                   ├─ GET /search?q=... ─►│                      │
│                   │                      ├─ Query products ────►│
│                   │                      │◄─ Return results ────┤
│                   │                      ├─ Get price_history ─►│
│                   │                      │◄─ Price data ────────┤
│                   │                      ├─ Get sentiment ─────►│
│                   │                      │◄─ Sentiment scores ──┤
│                   │                      ├─ Get forecast ──────►│
│                   │                      │◄─ Forecast data ─────┤
│                   │◄─ 200 OK + JSON ─────┤                      │
│◄─ Display results ┤  (products list)     │                      │
│  • Prices         │                      │                      │
│  • Charts         │                      │                      │
│  • PQS scores     │                      │                      │
│  • Forecast       │                      │                      │
│  • Recommendations│                      │                      │
```

---

## Hình 3-7: Sơ Đồ Tuần Tự - Use Case Crawl Dữ Liệu

```
Scheduler    Crawler         Playwright      Website          MongoDB
    │            │               │              │                 │
    ├─ Trigger ──►│               │              │                 │
    │  crawl task │               │              │                 │
    │            ├─ Launch ──────►│              │                 │
    │            │   headless     │              │                 │
    │            │   browser      │              │                 │
    │            │               ├─ Navigate ───►│                 │
    │            │               │   FPT Shop    │                 │
    │            │               │◄─ Load page ──┤                 │
    │            │               ├─ Scroll ──────►│                 │
    │            │               │  (lazy load)   │                 │
    │            │◄─ HTML ────────┤               │                 │
    │            ├─ Parse HTML    │               │                 │
    │            │  (BeautifulSoup)               │                 │
    │            ├─ Extract data: │               │                 │
    │            │  • Product name│               │                 │
    │            │  • Price       │               │                 │
    │            │  • Image URL   │               │                 │
    │            │  • Comments    │               │                 │
    │            │                │               │                 │
    │            ├─ Normalize data│               │                 │
    │            ├─ Upsert ──────────────────────────────────────► │
    │            │  (insert/update)               │                 │
    │            │◄──────────────────────────────────── OK ────────┤
    │            │                │               │                 │
    │            ├─ Trigger AI ──────────────────────────────────► │
    │            │  analysis      │               │ (PhoBERT)       │
    │            │                │               │                 │
    │            │ [Repeat for TGDĐ & ĐMX]        │                 │
    │            │                │               │                 │
    │◄─ Complete ┤                │               │                 │
    │            │                │               │                 │
```

---

## Hình 3-8: Sơ Đồ Tuần Tự - Use Case Phân Tích Cảm Xúc

```
MongoDB        AI Service       PhoBERT Model    MongoDB
(Comments)     (Processor)      (Fine-tuned)     (Results)
    │               │               │                  │
    ├─ Get new ───► │               │                  │
    │  comments     │               │                  │
    │◄─ Batch ──────┤               │                  │
    │  returned     │               │                  │
    │               ├─ Preprocess ──┤                  │
    │               │  • Remove punctuation           │
    │               │  • Normalize                    │
    │               │                                 │
    │               ├─ Tokenize ────►│                 │
    │               │◄─ Tokens ──────┤                 │
    │               │                                 │
    │               ├─ Embed & ──────►│                 │
    │               │  Classify       │                 │
    │               │◄─ Sentiment + ──┤                 │
    │               │  Aspects + Conf │                 │
    │               │                                 │
    │               ├─ Post-process ──┤                 │
    │               │  • Extract keywords             │
    │               │  • Compute RQS                  │
    │               │                                 │
    │               ├─ Save results ────────────────► │
    │               │  (sentiment_analysis)           │
    │               │◄─────────────────── Saved ──────┤
    │               │                                 │
    │               ├─ Update PQS ──────────────────► │
    │               │  (product_quality_score)        │
    │               │◄────────────────── Updated ─────┤
```

---

## Hình 3-9: Sơ Đồ Tuần Tự - Use Case Dự Báo Giá

```
MongoDB           LSTM Service        LSTM Model      MongoDB
(Price History)   (Processor)         (Pre-trained)   (Forecast)
    │                   │                  │              │
    ├─ Get price ──────►│                  │              │
    │  history (5-7d)   │                  │              │
    │◄─ Data ───────────┤                  │              │
    │  returned         │                  │              │
    │                   ├─ Clean data ────┤              │
    │                   │  • Fill missing values         │
    │                   │  • Remove outliers             │
    │                   │                                 │
    │                   ├─ Normalize ─────►│              │
    │                   │  (StandardScaler)│              │
    │                   │◄─ Normalized ───┤              │
    │                   │  data            │              │
    │                   │                  │              │
    │                   ├─ Reshape to ─────►│             │
    │                   │  LSTM input       │             │
    │                   │                  │              │
    │                   ├─ Predict ────────►│             │
    │                   │◄─ Forecast ──────┤              │
    │                   │  price + conf     │              │
    │                   │                  │              │
    │                   ├─ Inverse scale ──┤              │
    │                   │  (denormalize)    │              │
    │                   │                  │              │
    │                   ├─ Calculate metrics              │
    │                   │  (MAE, MAPE, Direction)        │
    │                   │                  │              │
    │                   ├─ Save forecast ─────────────► │
    │                   │  (forecast_results)            │
    │                   │◄──────────────────── Saved ───┤
```

---

## Hình 3-10: Dòng Chảy Dữ Liệu Tổng Quát (Data Flow Diagram)

```
┌─────────────────┐
│   3 Websites    │ (FPT Shop, TGDĐ, ĐMX)
└────────┬────────┘
         │ HTML/DOM
         │
    ┌────▼──────────────┐
    │   Crawler Module  │
    │  (Playwright +    │
    │   BeautifulSoup)  │
    └────┬──────────────┘
         │ Raw Data
         │
    ┌────▼──────────────────────┐
    │  Data Normalization       │
    │  • Clean names            │
    │  • Format prices          │
    │  • Extract comments       │
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────────┐
    │      MongoDB Database     │◄────┐
    │  (Store raw products      │     │
    │   & price history)        │     │
    └────┬──────────────────────┘     │
         │                             │
         ├─►┌──────────────────────┐   │
         │  │   PhoBERT Service    │   │ Feedback
         │  │ (Sentiment Analysis) │───┘
         │  └──────────────────────┘
         │           │
         │           ▼ sentiment_analysis results
         │       (MongoDB)
         │
         ├─►┌──────────────────────┐
         │  │   LSTM Service       │
         │  │ (Price Forecasting)  │
         │  └──────────────────────┘
         │           │
         │           ▼ forecast_results
         │       (MongoDB)
         │
         ├─►┌──────────────────────┐
         │  │  PQS Calculator      │
         │  │ (Quality Score)      │
         │  └──────────────────────┘
         │           │
         │           ▼
         │    product_quality_score
         │       (MongoDB)
         │
         ▼
    ┌──────────────────────┐
    │  FastAPI Backend     │
    │  • REST Endpoints    │
    │  • Search & Filter   │
    │  • Recommendations   │
    └──────────┬───────────┘
               │ JSON Response
               │
         ┌─────▼──────┐
         │  Frontend  │
         │  React.js  │
         └────────────┘
```

---

## Bảng 3-1: Tóm Tắt Các Thành Phần Hệ Thống

| Thành Phần | Công Nghệ | Chức Năng |
|-----------|----------|---------|
| **Frontend** | React.js + Vite | Giao diện web responsive, search, charts, dashboard |
| **Backend** | FastAPI + Python | API endpoints, business logic, user auth (Firebase) |
| **Crawler** | Playwright + BeautifulSoup | Tự động crawl FPT Shop, TGDĐ, ĐMX |
| **AI Module** | PhoBERT | Fine-tuned sentiment classification (3 labels) |
| **Forecasting** | LSTM (TensorFlow/Keras) | Dự báo giá dựa trên chuỗi thời gian |
| **Database** | MongoDB | Lưu 8 collection sản phẩm theo sàn (fpt, tgdd, cellphones, hoangha, didongviet, viettelstore, clickbuy, mobilecity), users, notifications |
| **Scheduler** | APScheduler | Chạy crawlers định kỳ (4-6 giờ) |
| **Authentication** | Firebase | Quản lý user, authentication tokens |
| **Model Storage** | Local files (.keras, .pkl) | Lưu trọng số LSTM, scalers, PhoBERT models |

---

## Bảng 3-2: Danh Sách Use Cases Chi Tiết

| Mã | Use Case | Scope | Actor |
|----|----------|-------|-------|
| UC1 | Tìm kiếm sản phẩm | Hệ thống | End User |
| UC2 | Xem PQS | Hệ thống | End User |
| UC3 | Xem lịch sử giá | Hệ thống | End User |
| UC4 | Xem phân tích cảm xúc | Hệ thống | End User |
| UC5 | Xem dự báo giá | Hệ thống | End User |
| UC6 | Nhận khuyến nghị mua | Hệ thống | End User |
| UC7 | So sánh multi-platform | Hệ thống | End User |
| UC8 | Crawl dữ liệu | Backend | System / Scheduler |
| UC9 | Phân tích sentiment | Backend | System |
| UC10 | Dự báo giá | Backend | System |

---

## Bảng 3-3: Đặc Tả Chi Tiết Các Use Case

| Mã | Tên Use Case | Tác Nhân | Mô Tả | Mối Quan Hệ | Kết Quả (Hậu Điều Kiện) |
|----|--------------|----------|-------|--------------|--------------------------|
| **UC1** | Tìm kiếm sản phẩm | End User | Người dùng nhập từ khóa tên sản phẩm (điện thoại) để tìm kiếm trên hệ thống. Hệ thống trả về danh sách sản phẩm phù hợp kèm giá, hình ảnh, URL từ các sàn TMĐT. | include: UC2, UC3, UC4, UC5, UC6, UC7 | Hiển thị danh sách sản phẩm với thông tin giá, PQS, sentiment, dự báo, khuyến nghị và so sánh đa nền tảng |
| **UC2** | Xem điểm chất lượng sản phẩm (PQS) | End User | Hệ thống tính toán và hiển thị điểm PQS (0-100) và hạng A/B/C/D/F dựa trên rating trung bình, điểm sentiment, độ tin cậy shop, số lượng bán và tỷ lệ đánh giá tích cực. | được include bởi UC1 | Hiển thị điểm PQS và xếp hạng chất lượng cho từng sản phẩm |
| **UC3** | Xem lịch sử giá & biểu đồ | End User | Hệ thống truy xuất dữ liệu `price_history` và hiển thị biểu đồ đường biến động giá theo thời gian cho sản phẩm được chọn. | được include bởi UC1 | Hiển thị biểu đồ lịch sử giá theo thời gian trên các nền tảng |
| **UC4** | Xem phân tích cảm xúc | End User | Hệ thống hiển thị kết quả phân tích sentiment (positive/negative/neutral) của các bình luận khách hàng, kèm tỷ lệ phần trăm và các khía cạnh (camera, pin, màn hình, giá, hiệu năng, thiết kế). | được include bởi UC1 | Hiển thị biểu đồ phân bố cảm xúc và các khía cạnh đánh giá |
| **UC5** | Xem dự báo giá | End User | Hệ thống hiển thị mức giá dự báo trong tương lai dựa trên mô hình LSTM, kèm hướng biến động (tăng/giảm/ổn định) và độ tin cậy (MAE, RMSE, MAPE). | được include bởi UC1 | Hiển thị mức giá dự báo, hướng biến động và độ tin cậy |
| **UC6** | Nhận khuyến nghị mua | End User | Hệ thống gợi ý hành động mua (BUY NOW / BUY / WAIT / CONSIDER / NOT RECOMMENDED) dựa trên kết hợp PQS và dự báo giá. | được include bởi UC1 | Hiển thị khuyến nghị mua kèm lý do cụ thể |
| **UC7** | So sánh giá đa nền tảng | End User | Hệ thống tổng hợp và so sánh giá của cùng một sản phẩm trên nhiều sàn (FPT Shop, TGDĐ, ĐMX...) để người dùng chọn nơi mua tốt nhất. | được include bởi UC1 | Hiển thị bảng so sánh giá giữa các nền tảng cho từng sản phẩm |
| **UC8** | Crawl dữ liệu | System / Scheduler | Scheduler kích hoạt crawler định kỳ (4-6 giờ) để thu thập dữ liệu sản phẩm, giá, bình luận từ các website TMĐT bằng Playwright + BeautifulSoup, sau đó chuẩn hóa và lưu vào MongoDB. | extend: UC9, UC10 | Dữ liệu sản phẩm, giá và bình luận mới được cập nhật vào MongoDB |
| **UC9** | Phân tích cảm xúc | System | Khi có bình luận mới được crawl, hệ thống chạy mô hình PhoBERT để phân loại sentiment và trích xuất các khía cạnh, cập nhật điểm RQS và PQS. | extend từ UC8 | Bảng `sentiment_analysis` được cập nhật, PQS được tính lại |
| **UC10** | Dự báo giá | System | Sau khi có đủ dữ liệu lịch sử giá (5-7 ngày), hệ thống dùng mô hình LSTM để dự báo giá tương lai, xác định hướng biến động và lưu vào `forecast_results`. | extend từ UC8 | Bảng `forecast_results` được cập nhật, phục vụ hiển thị dự báo |

---

## Bảng 3-4: Các Yêu Cầu Phi Chức Năng (Non-Functional Requirements)

| Mã | Loại Yêu Cầu | Mô Tả | Chỉ Tiêu / Ràng Buộc |
|----|--------------|-------|-----------------------|
| **NFR1** | Hiệu năng (Performance) | Thời gian phản hồi API tìm kiếm sản phẩm phải nhanh, đáp ứng trải nghiệm người dùng mượt mà. | Thời gian phản hồi trung bình ≤ 2 giây cho mỗi request tìm kiếm |
| **NFR2** | Hiệu năng (Performance) | Hệ thống phải xử lý được nhiều người dùng truy cập đồng thời mà không bị quá tải. | Hỗ trợ ≥ 100 người dùng đồng thời |
| **NFR3** | Khả năng mở rộng (Scalability) | Kiến trúc phân lớp (Presentation / Application / Data) cho phép mở rộng độc lập từng thành phần (crawler, AI service, backend). | Có thể thêm crawler mới hoặc mở rộng AI service mà không ảnh hưởng các module khác |
| **NFR4** | Độ tin cậy (Reliability) | Crawler chạy định kỳ phải hoạt động ổn định, xử lý được lỗi khi website thay đổi cấu trúc hoặc mất kết nối. | Tỷ lệ crawl thành công ≥ 95%; tự động retry khi thất bại |
| **NFR5** | Tính khả dụng (Availability) | Hệ thống phải luôn sẵn sàng phục vụ người dùng, đặc biệt trong giờ cao điểm. | Uptime ≥ 99% |
| **NFR6** | Bảo mật (Security) | Xác thực người dùng qua Firebase; bảo vệ API khỏi truy cập trái phép; không lộ thông tin nhạy cảm (service account key). | Mã hóa kết nối (HTTPS); xác thực token cho các endpoint; khóa bí mật không được commit lên repository |
| **NFR7** | Toàn vẹn dữ liệu (Data Integrity) | Dữ liệu crawl phải được chuẩn hóa (tên sản phẩm, định dạng giá) trước khi lưu để đảm bảo nhất quán khi so sánh. | Không trùng lặp sản phẩm; giá được chuẩn hóa về cùng đơn vị (VNĐ) |
| **NFR8** | Độ chính xác AI (AI Accuracy) | Mô hình PhoBERT và LSTM phải đạt độ chính xác chấp nhận được để đưa ra kết quả đáng tin cậy. | Sentiment accuracy ≥ 85%; dự báo giá MAPE ≤ 10% |
| **NFR9** | Khả năng sử dụng (Usability) | Giao diện web responsive, dễ sử dụng, hiển thị rõ ràng biểu đồ, điểm số và khuyến nghị. | Tương thích trình duyệt Chrome, Firefox, Edge; hỗ trợ thiết bị di động |
| **NFR10** | Khả năng bảo trì (Maintainability) | Mã nguồn được tổ chức theo module rõ ràng (backend, frontend, model, crawler), có tài liệu hướng dẫn. | Tuân thủ cấu trúc thư mục chuẩn; có README và tài liệu hướng dẫn chạy hệ thống |
| **NFR11** | Khả năng triển khai (Deployability) | Hệ thống được đóng gói bằng Docker để triển khai nhất quán trên nhiều môi trường. | Hỗ trợ `docker-compose up` để khởi động toàn bộ hệ thống |
| **NFR12** | Tính tương thích (Compatibility) | Hệ thống phải crawl được dữ liệu từ nhiều sàn TMĐT khác nhau (FPT Shop, TGDĐ, ĐMX...). | Hỗ trợ ≥ 3 nền tảng TMĐT; dễ dàng thêm nền tảng mới |
| **NFR13** | Khả năng giám sát (Observability) | Hệ thống ghi log quá trình crawl, xử lý AI và lỗi để dễ dàng theo dõi và gỡ lỗi. | Ghi log đầy đủ cho crawler, AI service, backend API |

---

## Thiết Kế Cơ Sở Dữ Liệu (Database Design)

### 1. Tổng Quan

Hệ thống sử dụng **MongoDB (NoSQL)** làm cơ sở dữ liệu chính (database `price_tracker`). Dữ liệu được tổ chức thành **10 collection**: **8 collection sản phẩm** (mỗi sàn TMĐT một collection riêng), **1 collection `users`** (người dùng) và **1 collection `notifications`** (thông báo).

### 2. Danh Sách Các Collection

| Collection | Mô Tả |
|------------|-------|
| `fpt` | Sản phẩm crawl từ FPT Shop |
| `tgdd` | Sản phẩm crawl từ Thế Giới Di Động |
| `cellphones` | Sản phẩm crawl từ CellphoneS |
| `hoangha` | Sản phẩm crawl từ Hoàng Hà Mobile |
| `didongviet` | Sản phẩm crawl từ Di Động Việt |
| `viettelstore` | Sản phẩm crawl từ Viettel Store |
| `clickbuy` | Sản phẩm crawl từ Clickbuy |
| `mobilecity` | Sản phẩm crawl từ MobileCity |
| `users` | Tài khoản người dùng, danh sách yêu thích, FCM token |
| `notifications` | Thông báo giá/khuyến nghị cho người dùng |

### 3. Chi Tiết Các Collection

#### 3.1 Collection Sản Phẩm (8 sàn: `fpt`, `tgdd`, `cellphones`, `hoangha`, `didongviet`, `viettelstore`, `clickbuy`, `mobilecity`)

Mỗi sàn TMĐT có một collection riêng, lưu trữ sản phẩm được crawl. Cấu trúc document giống nhau cho tất cả các sàn.

| Trường | Kiểu Dữ Liệu | Mô Tả |
|--------|-------------|-------|
| `_id` | ObjectId | Khóa chính (PK) |
| `platform` | String | Tên sàn TMĐT (FPT Shop / Thế Giới Di Động / ...) |
| `brand` | String | Hãng sản xuất (iphone / samsung / oppo / xiaomi) |
| `name` | String | Tên đầy đủ của sản phẩm |
| `model_base` | String | Tên model chuẩn hóa để so sánh giữa các sàn |
| `price_number` | Int | Giá hiện tại (VNĐ) — chuẩn hóa từ `price` |
| `price` | String/Int | Giá thô crawl từ website (có thể là chuỗi "29.990.000₫") |
| `image` / `image_url` | String | URL hình ảnh sản phẩm |
| `url` / `product_url` | String | URL trang sản phẩm trên sàn TMĐT |
| `rating` | Float | Điểm đánh giá trung bình (0-5) |
| `sold` | Int | Số lượng đã bán |
| `shop_reputation` | Float | Độ tin cậy của shop (0-100, mặc định 70) |
| `comments` | Array[String] | Danh sách bình luận của khách hàng |
| `price_history` | Array[Object] | Lịch sử giá: `[{scraped_at: Date, price: Int}]` |
| `forecast` | Int | Giá dự báo (LSTM) — lưu trên document sản phẩm |
| `last_crawl` | Date | Thời điểm crawl gần nhất (chuẩn hóa) |
| `last_scraped_at` | Date | Thời điểm crawl gần nhất (dữ liệu thô) |

**Chỉ mục (Indexes):**
- `{ url: 1 }` — unique index, dùng để upsert sản phẩm (tránh trùng lặp)
- `{ name: 1 }` — tìm kiếm sản phẩm theo tên (regex)
- `{ brand: 1 }` — lọc theo hãng
- `{ last_scraped_at: -1 }` — lấy sản phẩm mới nhất (search fallback)

#### 3.2 Collection: `users`

Lưu trữ tài khoản người dùng, danh sách sản phẩm yêu thích và FCM token.

| Trường | Kiểu Dữ Liệu | Mô Tả |
|--------|-------------|-------|
| `_id` | ObjectId | Khóa chính (PK) |
| `email` | String | Email đăng nhập (duy nhất, lowercase) |
| `password_hash` | String | Mật khẩu đã băm bằng bcrypt |
| `full_name` | String | Họ tên người dùng |
| `favorites` | Array[Object] | Danh sách sản phẩm yêu thích |
| `fcm_tokens` | Array[String] | FCM token để nhận push notification |
| `created_at` | Date | Thời điểm tạo tài khoản |

**Cấu trúc phần tử trong `favorites`:**

| Trường | Kiểu Dữ Liệu | Mô Tả |
|--------|-------------|-------|
| `platform` | String | Tên sàn TMĐT |
| `name` | String | Tên sản phẩm |
| `current_price` | Int | Giá tại thời điểm thêm |
| `forecast` | Int | Giá dự báo tại thời điểm thêm |
| `image` | String | URL hình ảnh |
| `link` | String | URL sản phẩm |
| `added_pqs` | Float | Điểm PQS tại thời điểm thêm |
| `added_at` | Date | Thời điểm thêm vào yêu thích |

**Chỉ mục (Indexes):**
- `{ email: 1 }` — unique index, tìm user theo email khi đăng nhập

#### 3.3 Collection: `notifications`

Lưu trữ thông báo cho người dùng (giá giảm, giá giảm sâu, giá thấp hơn trung bình, dự báo tăng giá, PQS tăng, nhiều bình luận tiêu cực).

| Trường | Kiểu Dữ Liệu | Mô Tả |
|--------|-------------|-------|
| `_id` | ObjectId | Khóa chính (PK) |
| `user_id` | String | ID người dùng nhận thông báo (tham chiếu `users._id`) |
| `key` | String | Khóa duy nhất để tránh trùng lặp thông báo |
| `type` | String | Loại: `price_drop` / `deep_drop` / `below_avg` / `forecast_up` / `pqs_up` / `negative_comments` |
| `title` | String | Tiêu đề thông báo |
| `message` | String | Nội dung thông báo |
| `product` | Object | Thông tin sản phẩm liên quan (platform, name, current_price...) |
| `created_at` | Date | Thời điểm tạo thông báo |
| `read` | Boolean | Trạng thái đã đọc (mặc định false) |

**Chỉ mục (Indexes):**
- `{ user_id: 1, created_at: -1 }` — lấy danh sách thông báo mới nhất của user
- `{ user_id: 1, key: 1 }` — unique index, tránh trùng lặp thông báo

### 4. Sơ Đồ Quan Hệ Giữa Các Collection

```
┌─────────────────────────────────────────────────────────────┐
│              DATABASE: price_tracker (MongoDB)              │
└─────────────────────────────────────────────────────────────┘

┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│    fpt    │  │   tgdd    │  │cellphones │  │  hoangha  │
│ (FPT Shop)│  │ (TGDĐ)    │  │(CellphoneS)│ │(Hoàng Hà) │
└───────────┘  └───────────┘  └───────────┘  └───────────┘

┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────┐
│ didongviet   │  │ viettelstore │  │ clickbuy  │  │ mobilecity │
│ (Di Động VN) │  │ (Viettel)    │  │ (Clickbuy)│  │(MobileCity)│
└──────────────┘  └──────────────┘  └───────────┘  └────────────┘
        (8 collection sản phẩm — cấu trúc giống nhau)

┌──────────────────┐          ┌──────────────────────┐
│      users       │ 1      N │    notifications     │
│  (người dùng)    │──────────│  (thông báo)         │
└──────────────────┘          └──────────────────────┘
```

**Ghi chú quan hệ:**
- **8 collection sản phẩm** độc lập nhau, mỗi collection đại diện cho một sàn TMĐT, có cùng cấu trúc document.
- Mỗi `users` có **nhiều** `notifications` (quan hệ 1-N) thông qua trường `user_id`.
- Mỗi `users` có **nhiều** sản phẩm yêu thích lưu trong mảng `favorites` (embedded document).

### 5. Chiến Lược Lưu Trữ

| Chiến Lược | Mô Tả |
|------------|-------|
| **Tách collection theo sàn** | Mỗi sàn TMĐT một collection riêng (`fpt`, `tgdd`, ...) để dễ quản lý và truy vấn độc lập |
| **Embedded Documents** | `users.favorites` lưu trực tiếp mảng sản phẩm yêu thích trong document user |
| **Embedded price_history** | `price_history` lưu trực tiếp trong document sản phẩm dưới dạng mảng `[{scraped_at, price}]` |
| **Upsert theo URL** | Dùng `url` làm khóa để upsert (insert/update) sản phẩm, tránh trùng lặp khi crawl lại |
| **Bù giá (Forward Fill)** | Khi hiển thị biểu đồ 7 ngày, ngày thiếu dữ liệu sẽ lấy giá ngày trước đó |

### 6. Ràng Buộc Toàn Vẹn Dữ Liệu

| Ràng Buộc | Mô Tả |
|-----------|-------|
| **Khóa chính** | Mỗi collection có `_id` (ObjectId) duy nhất |
| **Duy nhất email** | `users.email` là unique index — không cho phép trùng email |
| **Duy nhất URL** | Sản phẩm trong mỗi collection sàn có `url` unique — dùng làm khóa upsert |
| **Chuẩn hóa giá** | `price_number` luôn lưu dạng số nguyên VNĐ, chuyển từ chuỗi thô `price` bằng `parse_price()` |
| **Chuẩn hóa tên** | `model_base` được chuẩn hóa (lowercase, bỏ từ bổ trợ) để so sánh giữa các sàn |
| **Băm mật khẩu** | `password_hash` dùng bcrypt, không lưu mật khẩu dạng plain text |
| **Tránh trùng thông báo** | `notifications` dùng unique index `(user_id, key)` để tránh tạo thông báo trùng lặp |

---

**Lưu ý:** Các sơ đồ UML chi tiết hơn (đặc biệt là activity diagram, state diagram) nên được vẽ trong draw.io hoặc Enterprise Architect để có chất lượng cao hơn.

