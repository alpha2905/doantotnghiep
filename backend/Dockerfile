# Backend - FastAPI (ecommerce price comparison)
FROM python:3.10-slim

WORKDIR /app

# System deps cho numpy/scipy/scikit-learn + curl (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ backend (main.py, models/, *.py ...)
COPY backend/ ./backend/
WORKDIR /app/backend

# Render/Railway cấp PORT động; default 8000 khi chạy local
ENV PORT=8000
EXPOSE 8000

# 1 worker để tiết kiệm RAM free-tier (PhoBERT + LSTM đã nặng).
# Nếu gói trả phí, tăng workers theo RAM (mỗi worker ~1.5-2GB vì load AI models).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
