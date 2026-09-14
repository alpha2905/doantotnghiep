# Hướng dẫn Deployment lên Cloud

## 1. Push code lên GitHub

```bash
git add .
git commit -m "chore: prepare deployment configs"
git push origin main
```

## 2. Deploy Backend lên Render

### Cách A: Dùng Blueprint (khuyên dùng)

1. Vào https://dashboard.render.com → **New** → **Blueprint**
2. Kết nối repo GitHub
3. Render sẽ tự đọc `render.yaml` và tạo service `datn-price-api`
4. Khai báo các biến môi trường trong dashboard:

**Biến bắt buộc:**
- `MONGO_URI`: connection string MongoDB Atlas
- `ADMIN_EMAILS`: email admin (vd: `nguyenhoangan@example.com`)
- `FRONTEND_ORIGINS`: domain frontend sau khi deploy (vd: `https://datn-2905.web.app`)
- `FIREBASE_SERVICE_ACCOUNT_JSON`: nội dung JSON service account Firebase
- `EXPO_ACCESS_TOKEN`: Expo access token để gửi push notification (lấy từ https://expo.dev/accounts/account-name/settings/access-tokens)

**Biến tự động:**
- `JWT_SECRET_KEY`: Render tự generate
- `MONGO_DB_NAME`: đã mặc định `price_tracker`

5. Upload file `backend/serviceAccountKey.json` vào `/app/backend/` trong Render filesystem

6. Deploy → chờ ~3-5 phút → backend sẽ chạy tại `https://datn-price-api.onrender.com`

### Cách B: Deploy thủ công

```bash
# Cài Render CLI
npm install -g @render/cli

# Deploy
render services create
```

## 3. Deploy Frontend lên Firebase Hosting

### Bước 1: Build production

```bash
cd frontend
npm run build
```

Output nằm trong `frontend/dist/`

### Bước 2: Cập nhật API_URL trong code

Mở `frontend/dist/assets/index-*.js` và tìm `API_URL`, đổi thành URL backend thực tế:
```
https://datn-price-api.onrender.com
```

Hoặc tốt hơn: set biến môi trường trước khi build:
```bash
# Windows
$env:VITE_API_URL="https://datn-price-api.onrender.com"
npm run build

# Linux/Mac
VITE_API_URL=https://datn-price-api.onrender.com npm run build
```

Sau đó mở `frontend/vite.config.js` để inject biến môi trường vào build.

### Bước 3: Deploy lên Firebase

```bash
# Đăng nhập Firebase (chỉ cần 1 lần)
firebase login

# Deploy hosting
firebase deploy --only hosting
```

Sau khi deploy xong:
- Web URL: `https://datn-2905.web.app`
- Firebase sẽ tự động cấp HTTPS

### Bước 4: Cập nhật Backend CORS

Quay lại Render dashboard → chỉnh `FRONTEND_ORIGINS`:
```
https://datn-2905.web.app
```

Render sẽ tự động restart backend.

## 4. Build Mobile APK với EAS Build

### Bước 1: Đăng nhập Expo

```bash
cd mobile
npx expo login
```

### Bước 2: Cấu hình EAS Project (chỉ 1 lần)

```bash
eas build:configure
```

Trả lời các câu hỏi:
- Platform: Android
- Build profile: preview
- Distribution: internal/test

### Bước 3: Cập nhật API_URL cho mobile

Mở `mobile/app.json`, đổi `extra.apiUrl` thành URL backend thực tế:
```json
"extra": {
  "apiUrl": "https://datn-price-api.onrender.com"
}
```

### Bước 4: Build APK

```bash
eas build --platform android --profile preview
```

Quá trình build:
1. Upload code lên Expo cloud
2. Build APK trên cloud (~10-20 phút)
3. Nhận link tải APK qua email hoặc terminal

### Bước 5: Tải và cài APK

- Vào https://expo.dev/accounts/[account-name]/projects/smart-shopping-mobile/builds
- Tải APK về điện thoại Android
- Cài đặt (cho phép cài từ nguồn không xác định nếu cần)

## 5. Push Notifications - Test Production

### Backend

Đảm bảo các biến môi trường đã được set:
- `FIREBASE_SERVICE_ACCOUNT_JSON`: nội dung JSON service account
- `EXPO_ACCESS_TOKEN`: Expo access token

### Mobile

Khi user mở app lần đầu:
1. App gọi `registerForPushNotificationsAsync()` để lấy Expo push token
2. Gửi token lên backend qua `POST /api/fcm-token`
3. Backend lưu token vào DB

Khi có thông báo mới (giá thay đổi, sản phẩm yêu thích):
1. Backend query danh sách token của user
2. Tự động phát hiện token Expo → gửi qua Expo Push Service
3. Hoặc token FCM native → gửi qua Firebase Cloud Messaging
4. Người dùng nhận notification ngay cả khi app đóng

### Web

Firebase Cloud Messaging đã được cấu hình trong `frontend/public/firebase-messaging-sw.js`. Khi user cho phép notification trên web, họ sẽ nhận push notification qua FCM.

## 6. Tổng thứ tự deploy

```
1. Push code lên GitHub
   ↓
2. Deploy Backend (Render) → có URL API
   ↓
3. Build Frontend → set API_URL → Deploy Firebase Hosting → có URL web
   ↓
4. Cập nhật Backend: FRONTEND_ORIGINS = URL web
   ↓
5. Cập nhật Mobile: apiUrl = URL API → Build APK với EAS
   ↓
6. Test end-to-end: web search → add favorite → receive notification
```

## 7. URLs sau khi deploy

- **Backend API**: `https://datn-price-api.onrender.com`
- **Frontend Web**: `https://datn-2905.web.app`
- **Mobile APK**: Link từ Expo dashboard
- **Health Check**: `https://datn-price-api.onrender.com/health`

## 8. Monitoring & Maintenance

- **Render Dashboard**: xem logs, CPU/RAM usage, restart service
- **Firebase Console**: xem hosting traffic, performance
- **Expo Dashboard**: xem build status, OTA updates
- **MongoDB Atlas**: xem DB connections, storage usage

## 9. Troubleshooting

### Backend OOM (Out of Memory)
- Render free tier chỉ có 512MB RAM → không đủ cho PhoBERT + LSTM
- Giải pháp: nâng plan lên **Standard** (2GB RAM) trở lên

### Frontend build fail
- Kiểm tra `npm run build` chạy được không
- Nếu có lỗi Vite, xóa `node_modules/` và `package-lock.json` rồi `npm install` lại

### Mobile build fail
- Xem logs tại https://expo.dev/accounts/[account]/projects/smart-shopping-mobile/builds
- Thường do thiếu `serviceAccountKey.json` hoặc sai `apiUrl`

### Push notification không nhận được
- Kiểm tra token đã được lưu trong DB chưa: `db.fcm_tokens.find({})`
- Kiểm tra backend logs có lỗi gửi push không
- Đảm bảo điện thoại có kết nối internet
