# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài đặt công cụ build hệ thống (Cần thiết cho llama-cpp và các thư viện C++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Cài thư viện vào thư mục /install
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy thư viện đã cài từ builder
COPY --from=builder /install /usr/local

# Cài runtime dependencies (libpq5 cho postgres, curl cho healthcheck)
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

# Healthcheck
HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:2603/system/health || exit 1

# Chạy trực tiếp bằng Uvicorn
# --workers 2: Chạy 2 tiến trình song song
# --loop httptools: Có thể thêm nếu muốn tối ưu hiệu năng (nhưng uvicorn mặc định đã rất tốt)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "2603", "--workers", "2"]