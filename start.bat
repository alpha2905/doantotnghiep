@echo off
chcp 65001 >nul
cls

echo ╔══════════════════════════════════════════════════════════════════╗
echo ║      🚀 AI PRICE COMPARISON SYSTEM - BDUNHA                    ║
echo ║         Hệ thống so sánh giá & Phân tích cảm xúc              ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

:: Đường dẫn thư mục gốc
set PROJECT_DIR=%~dp0
set PROJECT_DIR=%PROJECT_DIR:~0,-1%
cd /d "%PROJECT_DIR%"

echo 📁 Thư mục dự án: %PROJECT_DIR%
echo.

:: Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Lỗi: Python không được cài đặt!
    echo 🌐 Vui lòng cài đặt Python 3.10+ tại https://python.org
    pause
    exit /b 1
)

echo ✅ Python đã sẵn sàng

:: Kiểm tra dependencies
echo 🔄 Kiểm tra dependencies...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 Đang cài đặt dependencies...
    pip install -r requirements.txt
)

echo ✅ Dependencies đã sẵn sàng
echo.
echo ✅ Sử dụng MongoDB Atlas (Cloud) - không cần MongoDB local
echo.

:: Khởi động Backend
echo 🚀 Khởi động Backend (FastAPI)...
cd /d "%PROJECT_DIR%\backend"
start "FastAPI Server" cmd /k "python main.py"
timeout /t 3 /nobreak >nul
echo ✅ Backend chạy tại http://127.0.0.1:8000
echo.

:: Khởi động Frontend
echo 🌐 Khởi động Frontend...
cd /d "%PROJECT_DIR%\frontend"
echo    Mở trình duyệt tại:
echo    http://127.0.0.1:3000
echo    hoặc mở file: %PROJECT_DIR%\frontend\index.html
echo.

:: Mở trình duyệt (nếu có)
start "" "http://127.0.0.1:8000/docs"
timeout /t 2 /nobreak >nul
echo 📚 API Docs: http://127.0.0.1:8000/docs
echo.

:: Hiển thị menu
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                     🎯 HỆ THỐNG ĐÃ SẴN SÀNG                     ║
echo ╠══════════════════════════════════════════════════════════════════╣
echo ║  📍 Truy cập: http://127.0.0.1:8000/docs                        ║
echo ║  📊 API: http://127.0.0.1:8000/api/compare                       ║
echo ║                                                                   ║
echo ║  🔧 Các cửa sổ đang chạy:                                         ║
echo ║     - FastAPI Server (Backend API)                               ║
echo ║     - Start.bat (Script chính)                                   ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo 💡 Để crawl dữ liệu, chạy: python fpt_crawl/fpt_crawl_ip.py
echo 💡 Scheduler tự động crawl: python scheduler.py
echo.
echo Nhấn phím bất kỳ để dừng hệ thống...
pause >nul

:: Dừng các process khi thoát
echo.
echo 🛑 Đang dừng hệ thống...
taskkill /F /FI "WINDOWTITLE eq FastAPI Server" >nul 2>&1
echo ✅ Đã dừng tất cả services!
echo.
echo Cảm ơn bạn đã sử dụng!
echo.
pause
