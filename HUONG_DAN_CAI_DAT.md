# Hướng dẫn cài đặt & chạy dự án

> **Smart Shopping Assistant** — Hệ thống so sánh giá sản phẩm & phân tích cảm xúc (Đồ án tốt nghiệp)
> Nguyễn Hoàng An – 22050040 – 25TH01 · GVHD: ThS. Dương Anh Tuấn

Dự án gồm **4 thành phần**: **Backend API (FastAPI)**, **Frontend Web (React + Vite)**, **Mobile App (Expo / React Native)**, và **MongoDB Atlas (cloud)**.

---

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản đề xuất |
|---|---|
| Python | **3.10+** (khuyến nghị 3.10.x) |
| Node.js | **18 LTS trở lên** (khuyến nghị 20 LTS) |
| npm / npx | đi kèm Node.js |
| MongoDB Atlas | Tài khoản + cluster cloud (không cần cài MongoDB local) |
| Firebase | *(tùy chọn)* cho push notification / hosting |
| Git | để clone repo |

> ⚠️ **Lưu ý dung lượng model:** Backend cần các file mô hình AI để chạy đầy đủ chức năng dự báo giá (LSTM) và phân tích cảm xúc (PhoBERT). Các file này **không được commit vào Git** (xem mục 2 và mục 11). Nếu bạn dùng bản nén nhẹ để nộp bài, xem mục **2.1 Bản nộp nhẹ** để biết cách khởi động lại các model.

---

## 2. Cấu trúc thư mục

```
ecommerce-price-comparison/
├── backend/                     # Backend FastAPI (thành phần chính)
│   ├── main.py                  # Entry point: uvicorn main:app
│   ├── auth.py, schema.py, firebase_helper.py, price_updater.py, scrapers.py ...
│   ├── config/pqs_weights.yaml  # Trọng số PQS/RQS
│   ├── models/                  # LSTM model + scaler  (general_lstm_best.pth, general_scaler.pkl)
│   ├── model/phobert_models/    # PhoBERT sentiment/aspect (final_model)  ← cần để NLU
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Mẫu biến môi trường
├── backend_new/                 # (Tùy chọn) backend tái cấu trúc thử nghiệm
├── frontend/                    # Web App React + Vite
│   └── package.json
├── mobile/                      # Mobile App Expo / React Native
│   └── package.json, app.json, eas.json
├── docker-compose.yml           # Chạy backend + frontend (nginx) bằng Docker
├── render.yaml                  # Blueprint deploy Render (backend)
├── DEPLOY.md                    # Hướng dẫn deploy chi tiết (Render / Firebase / EAS)
└── start.bat                    # Script khởi động nhanh trên Windows
```

### 2.1 Bản nộp nhẹ (submission light zip)

File `ecommerce-price-comparison-light.zip` đã loại bỏ các gói/thư mục nặng để phù hợp giới hạn nộp bài:
- **Không có:** `venv/`, `node_modules/`, `.git/`, `backend/model/phobert_models/`, `backend/models/general_scaler.pkl`, `data/`, `__pycache__/`, `android/.gradle/`, `android/build/`, `frontend/dist/`, `mobile/.expo/`, các file `.log`

**Để chạy backend đầy đủ từ bản nén nhẹ, bạn cần khởi động lại 2 model AI:**

1. **Retrain PhoBERT** (sentiment + aspect):
    ```bash
    python backend/scripts/train_phobert_from_labeled.py --epochs 15 --use-db-labeled
    ```
    Kết quả sẽ tạo ra:
    - `backend/model/phobert_models/sentiment_classification/final_model/`
    - `backend/model/phobert_models/aspect_classification/final_model/`

2. **Retrain LSTM** (để tạo cả `.pth` và `.pkl` scaler):
    ```bash
    python backend/scripts/train_lstm.py
    ```
    Kết quả sẽ ghi đè lên:
    - `backend/models/general_lstm_best.pth`
    - `backend/models/general_scaler.pkl`

Nếu bạn không cần chạy AI inference và chỉ muốn xem cấu trúc code/UI, có thể comment các lệnh load model trong `backend/main.py` (tuần tự dòng 106–172) và gán fallback cố định. Tuy nhiên, các endpoint `/api/compare`, `/api/search` sẽ bị ảnh hưởng vì thiếu dự báo giá và phân tích cảm xúc.

---

## 3. Chuẩn bị ban đầu

### 3.1. Clone repo

```bash
git clone https://github.com/alpha2905/doantotnghiep.git
cd ecommerce-price-comparison
```

### 3.2. Chuẩn bị MongoDB Atlas

Dự án mặc định tự động kết nối tới cluster cloud `giasanpham.uqyaw1p.mongodb.net` (đã nhúng URI trong code), nên **chạy local thông thường không cần tạo tài khoản mới**. Nếu bạn muốn dùng database riêng thì đổi biến `MONGO_URI` (xem mục 8).

---

## 4. Cài đặt Backend

### 4.1. Tạo môi trường ảo (khuyến nghị)

```bash
cd backend
python -m venv venv

# Windows (cmd/PowerShell)
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 4.2. Cài Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3. Cài trình duyệt Playwright (cần cho crawler 8 sàn)

```bash
python -m playwright install chromium
```

> Chỉ cần bước này khi bạn muốn **crawl dữ liệu** (mục 7). Không bắt buộc để chạy API đọc dữ liệu.

### 4.4. Cấu hình biến môi trường (tùy chọn)

Backend chạy được ngay với giá trị mặc định (URI MongoDB + JWT secret đều đã nhúng). Nếu cần tùy chỉnh, hãy tạo file `.env` từ mẫu:

```bash
copy .env.example .env        # Windows
cp .env.example .env           # Linux / macOS
```

> Ghi chú: code đọc biến qua `os.environ.get(...)`. Bật file `.env` bằng cách cài **python-dotenv** (`pip install python-dotenv`) và gọi `load_dotenv()` nếu bạn muốn tự động nạp; hiện tại bạn có thể set biến trực tiếp trước khi start (xem mục 4.5).

### 4.5. Chạy Backend

```bash
cd backend

# Cách 1: dùng uvicorn (khuyến nghị, có auto-reload khi phát triển)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Cách 2: chạy trực tiếp (tương đương, không tự reload)
python main.py
```

Backend sẽ khởi động và **load mô hình AI**:
- `✅ PyTorch LSTM Model loaded` (dự báo giá)
- `✅ AI Models Ready!` (PhoBERT sentiment + aspect)
- `ℹ️ Background price updater DISABLED` (bình thường – crawler chạy thủ công)

### 4.6. Kiểm tra Backend

Mở trình duyệt:

| URL | Nội dung |
|---|---|
| `http://127.0.0.1:8000/docs` | Swagger UI – danh sách toàn bộ API |
| `http://127.0.0.1:8000/health` | Kiểm tra sức khỏe (trả về `ok: true`) |
| `http://127.0.0.1:8000/api/compare?name=iphone%2015&brand=apple` | So sánh giá 3 sàn rẻ nhất |
---

## 5. Cài đặt Frontend (Web)

```bash
cd frontend
npm install
npm run dev
```

Frontend Vite sẽ chạy tại **`http://127.0.0.1:5173`** (mặc định Vite). `src/App.jsx` mặc định gọi backend tại `http://127.0.0.1:8000`, nên nếu backend đã chạy thì web hoạt động ngay.

**Tùy chỉnh URL backend (quan trọng khi deploy):**

```bash
# Tạo file .env trong thư mục frontend
copy .env.example .env      # Windows
```
```env
VITE_API_URL=https://<ten-service-cua-ban>.onrender.com
```

**Build bản production:**

```bash
npm run build        # xuất ra thư mục dist/ (cho Firebase Hosting / nginx)
npm run preview      # xem thử bản build local
```

---

## 6. Cài đặt Mobile App (Expo / React Native)

```bash
cd mobile
npm install
npx expo start
```

Quét mã QR bằng **Expo Go** (thiết bị thật) hoặc nhấn `a` để mở Android Emulator / `w` để mở trên web.

> **Quan trọng:** URL backend của mobile được đọc từ `app.json → extra.apiUrl` (hiện là IP LAN mặc định `http://192.168.2.16:8000`) hoặc biến `EXPO_PUBLIC_API_URL`. Trước khi test hãy đổi thành đúng máy chạy backend:
>
> ```env
> # file mobile/.env (tạo từ .env.example)
> EXPO_PUBLIC_API_URL=http://<IP-máy-backend>:8000
> ```
> - **Thiết bị thật:** dùng IP LAN của máy tính (vd `http://192.168.1.10:8000`), cùng mạng WiFi với backend.
> - **Android Emulator:** dùng `http://10.0.2.2:8000` (alias host của emulator).

**Build APK/AAB bằng EAS** (cấu hình sẵn trong `eas.json`):

```bash
npx eas login
npx eas build -p android --profile preview      # APK để test
npx eas build -p android --profile production   # AAB cho CH Play
```

---

## 7. Crawl dữ liệu 8 sàn TMĐT

Backend chỉ đọc dữ liệu đã có trong MongoDB. Để cập nhật giá/sản phẩm/bình luận mới, chạy crawler:

```bash
cd backend
python scrape_comments.py        # crawl bình luận
python scrape_ratings.py         # crawl rating/sao

# Hoặc chạy scraper giá nhanh trên Windows bằng script:
# ..\run_local_scraper.bat
```

> Lịch crawler tự động đang **TẮT** theo mặc định (đã comment trong `main.py`). Chạy thủ công khi cần — đây là thiết kế hiện tại của project.
---

## 8. Bảng biến môi trường quan trọng

| Biến | Mô tả | Mặc định |
|---|---|---|
| `MONGO_URI` | Chuỗi kết nối MongoDB Atlas | đã nhúng trong code |
| `MONGO_DB` / `MONGO_DB_NAME` | Tên database | `price_tracker` |
| `JWT_SECRET_KEY` | Bí mật ký token | giá trị mặc định (nên đổi khi prod) |
| `ADMIN_EMAILS` | Danh sách email admin (cách nhau dấu phẩy) | — |
| `FRONTEND_ORIGINS` | CORS cho web (cách nhau dấu phẩy) | `*` |
| `PORT` | Cổng backend | `8000` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Đường dẫn `serviceAccountKey.json` Firebase | — |
| `EXPO_ACCESS_TOKEN` | Token đẩy thông báo Expo (mobile) | — |
---

## 9. Chạy nhanh tất cả bằng một lệnh (Windows)

Nếu backend chưa có dependencies, dùng script sẵn có ở root:

```bat
start.bat
```

Script sẽ: kiểm tra Python → tự `pip install -r requirements.txt` (nếu thiếu `fastapi`) → mở backend tại `http://127.0.0.1:8000` và swagger docs.

---

## 10. Deploy

Chi tiết đầy đủ xem file **[DEPLOY.md](./DEPLOY.md)** và **[render.yaml](./render.yaml)**. Tóm tắt nhanh:

| Thành phần | Nền tảng | Cách làm |
|---|---|---|
| Backend | Render (Docker) | Import repo → dùng `render.yaml` (Blueprint); set biến môi trường `MONGO_URI`, `FRONTEND_ORIGINS`, `ADMIN_EMAILS`, `FIREBASE_SERVICE_ACCOUNT_JSON` |
| Frontend | Firebase Hosting | `cd frontend && npm run build && firebase deploy --only hosting` (project: `datn-2905`) |
| Mobile | EAS / Expo | `npx eas build -p android` |
---

## 11. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân & khắc phục |
|---|---|
| `pip install` lỗi build tensorflow/torch | Dùng Python 3.10 64-bit; nếu vẫn lỗi, cài riêng `torch` từ Pytorch index trước. |
| Backend in `❌ AI Error: FileNotFoundError` cho PhoBERT | Thiếu `backend/model/phobert_models/.../final_model`. Bỏ models vào đúng đường dẫn (xem mục 2). |
| `playwright` lỗi khi crawl | Chưa chạy `python -m playwright install chromium`. |
| Frontend gọi API bị lỗi CORS | Set `FRONTEND_ORIGINS` đúng URL frontend rồi restart backend. |
| Mobile không gọi được backend | Sai `EXPO_PUBLIC_API_URL` hoặc `extra.apiUrl`; thiết bị phải cùng mạng / đúng cổng. |
| `eas build` lỗi | `eas.json` chứa `projectId` placeholder; chạy `npx eas init` để cấu hình project thật. |
| **Dùng bản nén nhẹ mà backend báo `FileNotFoundError` PhoBERT / LSTM scaler** | File `phobert_models/` và `general_scaler.pkl` bị loại bỏ khỏi zip. Chạy `python backend/scripts/train_phobert_from_labeled.py --epochs 15 --use-db-labeled` và `python backend/scripts/train_lstm.py` để tạo lại model trước khi start API. |

---

## 12. Lưu ý bảo mật

- **Không commit** `serviceAccountKey.json`, file `.env`, `.env.local`, `*.keystore` lên Git (`.gitignore` đã chặn).
- Đổi `JWT_SECRET_KEY` và set `ADMIN_EMAILS` khi deploy production.
- Các file model (hàng trăm MB – GB) **không nên** đẩy lên Git; nếu cần chia sẻ hãy dùng Git LFS hoặc lưu trữ ngoài repo.