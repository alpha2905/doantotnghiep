# Smart Shopping Assistant - Backend API

## Tổng quan

Hệ thống Smart Shopping Assistant tích hợp phân tích cảm xúc và dự báo xu hướng giá sản phẩm. Backend được xây dựng bằng FastAPI, kết nối MongoDB Atlas, và tích hợp các mô hình AI:

- **PhoBERT**: Phân tích cảm xúc bình luận (Sentiment Analysis) và phân loại khía cạnh (Aspect Classification)
- **LSTM**: Dự báo xu hướng biến động giá sản phẩm
- **Entity Resolution**: Ghép nối sản phẩm trùng lặp từ nhiều sàn TMĐT
- **PQS/RQS**: Chỉ số đánh giá chất lượng sản phẩm và bình luận

## Cấu trúc thư mục

```
backend/
├── main.py                      # FastAPI app chính
├── config/
│   └── pqs_weights.yaml         # Trọng số PQS và cơ sở heuristic
├── model/
│   ├── train_phobert.py         # Huấn luyện PhoBERT Sentiment + Aspect
│   ├── train_lstm.py            # Huấn luyện LSTM dự báo giá
│   ├── evaluate_phobert_hybrid.py   # Đánh giá Sentiment: Rule vs PhoBERT vs Hybrid
│   ├── evaluate_aspect_model.py     # Đánh giá Aspect Classification
│   ├── evaluate_lstm_temporal.py    # Đánh giá LSTM với temporal split
│   ├── evaluate_entity_resolution.py # Đánh giá Entity Resolution
│   ├── evaluate_pqs_rqs_recommendation.py  # Unit test PQS/RQS
│   ├── experiment_runner.py     # Chạy thống nhất tất cả thí nghiệm
│   ├── phobert_models/          # Pre-trained PhoBERT models
│   └── results/                 # Kết quả đánh giá JSON
├── metrics.py                   # Standardized metrics: MAE, RMSE, MAPE, sMAPE, Direction Accuracy
├── background_workers.py        # Background task phân tích bình luận
├── load_test.py                 # API load test thực (P95, P99, throughput)
├── scrape_comments.py           # Crawl bình luận từ 8 sàn TMĐT
├── scrape_ratings.py            # Crawl rating/sao đánh giá
├── models/                      # LSTM model + scaler
└── serviceAccountKey.json       # Firebase credentials
```

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy Backend

```bash
# Windows PowerShell
$env:MONGO_URI="mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Chạy Thí nghiệm (Chapter 4)

### 1. Đánh giá PhoBERT Sentiment + Hybrid Engine

```bash
python backend/model/evaluate_phobert_hybrid.py
```

Kết quả:
- Accuracy, Macro-F1, Weighted-F1
- Per-class Precision/Recall/F1
- Confusion Matrix
- Latency measurement

### 2. Đánh giá Aspect Classification

```bash
python backend/model/evaluate_aspect_model.py
```

Kết quả:
- Per-class Precision/Recall/F1
- Macro-F1 vs Weighted-F1 (phân tích mất cân bằng)
- Class distribution table
- Confusion Matrix

### 3. Đánh giá LSTM Price Forecast

```bash
python backend/model/evaluate_lstm_temporal.py
```

Kết quả:
- Temporal split 80/20
- So sánh với baselines: Naive, Moving Average 3/7 ngày, Last Value
- Multi-LOOK_BACK: 5, 7, 14, 30 ngày
- MAE, RMSE, MAPE, Direction Accuracy

### 4. Đánh giá Entity Resolution

```bash
python backend/model/evaluate_entity_resolution.py
```

Kết quả:
- Ground truth Precision/Recall/F1 tại các threshold
- Phân tích near-threshold cases
- Ngưỡng tối ưu và ngưỡng vận hành

### 5. Đánh giá PQS/RQS

```bash
# Unit test
python backend/model/evaluate_pqs_rqs_recommendation.py

# Trên DB thực
python backend/model/evaluate_pqs_rqs_recommendation_db.py
```

### 6. Chạy tất cả thí nghiệm

```bash
python backend/model/experiment_runner.py --all --report
```

### 7. Crawler Benchmark

```bash
python backend/scrape_ratings.py --limit 10
python backend/scrape_comments.py --limit 10
```

### 8. API Load Test

```bash
# Đảm bảo API đang chạy
python backend/load_test.py --workers 1 10 25 50 --requests 10
```

Hoặc dùng script tích hợp:

```bash
python backend/benchmark_api.py
```

## Cấu hình

### PQS Weights

File `backend/config/pqs_weights.yaml` chứa trọng số PQS:

```yaml
pqs_weights:
  rating: 0.25          # Đánh giá sao cửa hàng
  sentiment: 0.30       # Phân tích cảm xúc bình luận (PhoBERT)
  shop_reputation: 0.15 # Uy tín cửa hàng/sàn
  positive_rate: 0.15   # Tỷ lệ bình luận tích cực
  sold_volume: 0.15     # Số lượng đã bán
```

**Lưu ý**: Các trọng số này là heuristic của prototype, chưa được tối ưu hóa bằng khảo sát người dùng.

## Mobile App Status

**Trạng thái**: Mobile Prototype (Flutter/React Native)

- Giao diện Mobile đang ở mức prototype, chưa được build và test trên thiết bị thực
- Push Notification (Firebase Cloud Messaging) đã được tích hợp vào backend
- Chức năng chính: tìm kiếm sản phẩm, so sánh giá, xem biểu đồ lịch sử giá, nhận thông báo giảm giá

## Deployment

### Kiến trúc hệ thống

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Web App   │────▶│  FastAPI     │────▶│  MongoDB    │
│  (React.js) │     │  Backend     │     │  Atlas      │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├─────────────────┐
                           │                 │
                    ┌──────▼──────┐   ┌──────▼──────┐
                    │ Background  │   │  PhoBERT /  │
                    │ Workers     │   │  LSTM AI    │
                    │ (Celery)    │   │  Service    │
                    └─────────────┘   └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Crawler    │
                    │  (Playwright│
                    │  + BS4)     │
                    └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  8 Sàn TMĐT │
                    │  (FPT, TGDD │
                    │  CellphoneS │
                    │  ...)       │
                    └─────────────┘
```

### Triển khai

- **Backend**: AWS EC2 / Railway / Render
- **Database**: MongoDB Atlas (cluster đã có sẵn)
- **AI Models**: Lưu trong backend/models, load tại startup
- **Crawler**: Chạy như background worker hoặc cron job
- **Web**: Deploy trên Vercel / Netlify / AWS S3 + CloudFront

## Các cải tiến chính theo góp ý giảng viên

| STT | Nội dung | Trạng thái |
|-----|----------|-----------|
| 1 | Bổ sung kết quả định lượng Chương 4 | ✅ Đã tạo framework |
| 2 | Standardize Train/Val/Test 80/10/10 | ✅ Đã sửa |
| 3 | Per-class Precision/Recall/F1 | ✅ Đã thêm |
| 4 | Xử lý mất cân bằng Aspect | ✅ Đã báo cáo imbalance ratio |
| 5 | Chứng minh Hybrid Engine tốt hơn | ✅ Đã có so sánh Rule vs PhoBERT vs Hybrid |
| 6 | LSTM temporal split + baseline | ✅ Đã thêm |
| 7 | Test LOOK_BACK 5/7/14/30 | ✅ Đã thêm |
| 8 | Sửa logic MAE/RMSE/MAPE | ✅ Đã dùng metrics.py chuẩn |
| 9 | Không padding giá thiếu | ✅ Đã xóa forward-fill |
| 10 | Entity Resolution ground truth | ✅ Đã có 20 cặp ground truth |
| 11 | Làm rõ PQS/RQS weights | ✅ Đã tạo pqs_weights.yaml |
| 12 | Background Worker cho comments | ✅ Đã tạo background_workers.py |
| 13 | Thống nhất crawler frequency | ⏳ Cần cập nhật config |
| 14 | API Load Test thực tế | ✅ Đã tạo load_test.py |
| 15 | Mobile App status | ✅ Đã ghi rõ là prototype |

## Lưu ý quan trọng

1. **TensorFlow/Keras**: Backend hiện tại không phụ thuộc TensorFlow. Nếu cần chạy PhoBERT/LSTM, dùng PyTorch.
2. **MongoDB**: Sử dụng MongoDB Atlas cluster `giasanpham.uqyaw1p.mongodb.net`
3. **Firebase**: Push notification yêu cầu `serviceAccountKey.json` trong thư mục backend/
4. **Crawler**: Chạy thủ công khi cần cập nhật dữ liệu, không chạy tự động trong production

## Tác giả

Nguyễn Hoàng An - 22050040 - 25TH01  
GVHD: ThS. Dương Anh Tuấn
