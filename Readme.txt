1. YÊU CẦU HỆ THỐNG
Máy tính đã cài đặt Docker Desktop.

Kết nối Internet (để tải thư viện AI và các giao diện).

2. CẤU TRÚC THƯ MỤC
📁 backend/: Mã nguồn API (FastAPI), xử lý PhoBERT và LSTM.

📁 frontend/: Giao diện người dùng (HTML, Tailwind CSS, Chart.js).

📁 init-db/: Chứa file data_backup.archive (Dữ liệu mẫu đã crawl).

📄 docker-compose.yml: File điều phối toàn bộ hệ thống.

3. CÁC BƯỚC KHỞI CHẠY (QUAN TRỌNG)
Bước 1: Mở Terminal (PowerShell hoặc CMD) tại thư mục gốc của đồ án.

Bước 2: Chạy lệnh để tự động xây dựng môi trường:
docker-compose up -d --build

(Lưu ý: Lần đầu tiên chạy, Docker sẽ tải các thư viện nặng như PyTorch và TensorFlow, có thể mất từ 5-10 phút tùy tốc độ mạng).

Bước 3: Sau khi các Container báo Running, truy cập các địa chỉ sau:

Giao diện Dashboard: http://localhost:3000

Tài liệu API (Swagger): http://localhost:8000/docs

4. LƯU Ý KỸ THUẬT
Dữ liệu: Hệ thống được tích hợp cơ chế tự động khôi phục dữ liệu từ file .archive trong thư mục init-db vào MongoDB ngay khi khởi động.

Mô hình AI: * Mô hình PhoBERT thực hiện phân tích cảm xúc bình luận trực tiếp.

Mô hình LSTM thực hiện dự báo giá dựa trên lịch sử giá đã thu thập.

Cổng kết nối: Nếu máy có xung đột cổng 3000 hoặc 8000, vui lòng chỉnh sửa ở cột bên trái trong file docker-compose.yml.