FROM python:3.10-slim

WORKDIR /app

# Chỉ cài gói cơ bản để tải trình duyệt
RUN apt-get update && apt-get install -y wget gnupg && rm -rf /var/lib/apt/lists/*

# Cài đặt thư viện Python trước
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir fastapi uvicorn motor pymongo pandas numpy scikit-learn pyvi playwright beautifulsoup4 requests
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir tensorflow-cpu

# ĐÂY LÀ DÒNG QUAN TRỌNG: Tự động cài thư viện hệ thống chuẩn cho Playwright
RUN playwright install chromium --with-deps

COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]