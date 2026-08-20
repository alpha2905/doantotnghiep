@echo off
chcp 65001 >nul
title Scraper 8 sàn - Local
cd /d "%~dp0backend"

echo ============================================
echo   SCRAPER 8 SAN - CHAY TREN MAY LOCAL
echo ============================================
echo.
echo [1] Chay 1 lan (cap nhat gia thuc)
echo [2] Chay lap moi 3 gio
echo [3] Chay thu (dry-run, khong ghi DB)
echo [4] Thoat
echo.
set /p choice="Chon (1-4): "

if "%choice%"=="1" (
    python run_local_scraper.py --once
) else if "%choice%"=="2" (
    python run_local_scraper.py --interval 3
) else if "%choice%"=="3" (
    python run_local_scraper.py --once --dry-run
) else (
    echo Thoat.
    pause
    exit /b
)

echo.
pause