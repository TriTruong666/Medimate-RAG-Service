# Medimate RAG Service

Medimate RAG Service là một hệ thống Retrieval-Augmented Generation (RAG) được xây dựng trên nền tảng FastAPI, cung cấp khả năng quản lý tài liệu và truy vấn thông tin thông minh sử dụng các mô hình ngôn ngữ lớn (LLM) chạy cục bộ.

## 🚀 Tính năng chính

- **Quản lý tài liệu:** Hỗ trợ tải lên và xử lý các định dạng tệp phổ biến như `.pdf`, `.docx`, `.txt`.
- **Công cụ RAG mạnh mẽ:** Sử dụng LlamaIndex với cơ chế `HierarchicalNodeParser` và `AutoMergingRetriever` để tối ưu hóa việc truy xuất thông tin.
- **Hỗ trợ LLM cục bộ:** Chạy các mô hình định dạng `.gguf` (Qwen, Llama, v.v.) giúp bảo mật dữ liệu và tiết kiệm chi phí.
- **Cơ sở dữ liệu Vector:** Kết hợp PostgreSQL với extension `pgvector` và ChromaDB để lưu trữ và tìm kiếm vector hiệu quả.
- **API chuẩn RESTful:** Dễ dàng tích hợp với các ứng dụng frontend hoặc dịch vụ khác.

## 🛠 Công nghệ sử dụng

- **Backend:** FastAPI
- **RAG Framework:** LlamaIndex
- **Database:** PostgreSQL (với pgvector), SQLAlchemy, ChromaDB
- **Mô hình AI:** sentence-transformers (Embedding), GGUF Models (LLM)
- **Containerization:** Docker & Docker Compose

## 📋 Yêu cầu hệ thống

Trước khi bắt đầu, hãy đảm bảo bạn đã cài đặt:
- **Python 3.10+**
- **C++ Build Tools:** Cần thiết để biên dịch một số thư viện như `llama-cpp-python`.
  - [Tải Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) và chọn **"Desktop development with C++"**.
- **PostgreSQL:** Với extension `pgvector` (Khuyên dùng chạy qua Docker).

## ⚙️ Cài đặt & Thiết lập

### 1. Khởi tạo môi trường ảo

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 2. Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### 3. Cấu hình cơ sở dữ liệu

Sử dụng Docker Compose để khởi chạy PostgreSQL với pgvector:

```bash
docker-compose up -d
```

Hãy đảm bảo bạn đã tạo file `.env` và cấu hình `RAG_DB_URL`.

### 4. Tải mô hình AI

Dự án sử dụng các mô hình định dạng `.gguf`.
- Tạo thư mục `app/models_weights/`.
- Tải mô hình (ví dụ: Qwen2.5-1.5B-Instruct-GGUF) và đặt vào thư mục trên.
- Cấu hình đường dẫn mô hình trong `app/core/config.py` hoặc qua biến môi trường.

### 5. Chuẩn bị dữ liệu

- Tạo thư mục `data/raw_data/` để chứa các file tài liệu tải lên (như được định nghĩa trong `settings.RAW_UPLOAD_PATH`).

## 🏃 Chạy ứng dụng

Khởi chạy server FastAPI:

```bash
python main.py
```

Ứng dụng sẽ chạy tại: `http://localhost:8000`. Bạn có thể truy cập tài liệu API (Swagger UI) tại: `http://localhost:8000/docs`.

## 📂 Cấu trúc thư mục

```text
.
├── app/
│   ├── api/            # Định nghĩa các endpoints và routes
│   ├── core/           # Cấu hình hệ thống, database và utilities
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Logic nghiệp vụ (Document, RAG Engine, etc.)
│   └── data/           # Dữ liệu lưu trữ cục bộ (ChromaDB, Metadata)
├── data/
│   └── raw_data/       # Thư mục chứa tài liệu tải lên
├── main.py             # File khởi chạy ứng dụng
├── docker-compose.yml  # Cấu hình Docker cho Database
└── requirements.txt    # Danh sách thư viện phụ thuộc
```

## 📝 Tài liệu API (Sơ lược)

- **Documents:**
  - `POST /api/v1/documents/upload-document`: Tải lên tài liệu mới.
  - `GET /api/v1/documents/`: Lấy danh sách tài liệu (hỗ trợ phân trang và tìm kiếm).
- **System:**
  - `GET /system/health`: Kiểm tra trạng thái hoạt động của server.

---
Phát triển bởi **TriTruong666**.
