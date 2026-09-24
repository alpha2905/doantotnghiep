@echo off
chcp 65001 >nul
echo ============================================
echo    TRAINING PHOBERT - GPU / 15 EPOCHS
echo ============================================
echo.

cd /d "%~dp0"

if exist "..\..\venv\Scripts\activate.bat" (
    echo [INFO] Kich hoat venv...
    call "..\..\venv\Scripts\activate.bat"
)

echo [INFO] Dang train PhoBERT...
echo [INFO] GPU se duoc su dung neu co san.
echo.

python train_phobert_from_labeled.py --epochs 15 --use-db-labeled

echo.
echo ============================================
echo    HOAN TAT
echo ============================================
pause
