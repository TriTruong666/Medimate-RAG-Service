# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài đặt công cụ build hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Cài thư viện vào thư mục /install để copy sang stage sau cho nhẹ
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy thư viện đã cài từ builder
COPY --from=builder /install /usr/local

# Cài runtime dependencies cho Postgres và Curl để healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy mã nguồn
COPY . .

# Tạo sẵn các thư mục cần thiết
RUN mkdir -p data/raw_data app/models_weights logs seeds

EXPOSE 2603

# Healthcheck chuẩn Prod
HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:2603/system/health || exit 1

# Chạy bằng Gunicorn để quản lý worker tốt hơn
CMD ["gunicorn", "main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:2603", \
     "--timeout", "120"]