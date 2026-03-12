# Medimate RAG Service - Hướng Dẫn Dành Cho Developer

Chào mừng bạn đến với tài liệu hướng dẫn phát triển và quản lý mã nguồn cho **Medimate RAG Service**. 
Tài liệu này được định hướng để giúp bạn trong nhóm kế thừa nhanh chóng nắm bắt luồng hệ thống, cấu trúc thư mục, và các bước cần thiết để làm chủ cũng như tiếp tục quản lý dự án này.

## 🚀 Tổng quan về Hệ Thống

Dự án này là một dịch vụ RAG (Retrieval-Augmented Generation) chuyên biệt dựa trên **FastAPI**, **LlamaIndex**, và **PostgreSQL (pgvector)**. 
Hệ thống cung cấp các tính năng:
- Tải lên, băm nhỏ và xử lý tài liệu đa định dạng (PDF, DOCX, TXT) để trích xuất vector ngữ nghĩa.
- Nhúng (embed) và tìm kiếm thông tin theo độ tương đồng bằng `sentence-transformers`.
- Sinh câu trả lời trả về cho người dùng qua các mô hình ngôn ngữ lớn (LLM) cục bộ lưu trữ theo định dạng `.gguf`.
- Quản lý trạng thái như metadata dữ liệu, lịch sử hội thoại và cấu hình độ nhạy từ RAG DB.

## 📁 Cấu Trúc Mã Nguồn (Khoanh vùng Quản Lý)

Dự án đang được chia tách tương đối chuẩn theo cấu trúc phân tầng, vì vậy hãy giữ nguyên triết lý **không trộn lẫn logic vào API Routes**:

```text
.
├── app/
│   ├── api/            # Tầng Controller (Tiếp nhận request)
│   │   ├── endpoints/  # Chứa các file API cho từng nhóm (documents.py, chat.py, rag_config.py)
│   │   └── routes.py   # Ghép nối các endpoints lại thành 1 router tổng
│   ├── core/           # Tầng cấu hình lõi
│   │   ├── common/     # Định dạng trả về tiêu chuẩn (Interceptor, Responses)
│   │   ├── db/         # Cấu hình khởi tạo Database
│   │   └── config.py   # Load các tham số môi trường từ tham số .env
│   ├── models/         # Entity / SQLAlchemy Models đại diện cấu trúc bảng Database
│   ├── schemas/        # Pydantic Models (Chỉ dùng để Ràng buộc/Validate Data API)
│   └── services/       # Tầng Nghiệp Vụ Chính (Heart of the app)
│       ├── chat_service.py       # Hỏi đáp AI RAG
│       ├── document_service.py   # Xử lý upload, chunk nội dung
│       ├── file_service.py       # Xử lý lưu trữ vật lý files
│       ├── rag_engine.py         # Set up hệ thống LlamaIndex RAG
│       ├── model_loader.py       # Tải/Cash LLMs và Embedding models 
│       └── rag_config_service.py # API Cấu hình thông số model
├── data/
│   ├── raw_data/       # Mặc định: Nơi chứa tài liệu thô được upload lên server.
│   └── chromadb/       # (Tuỳ thuộc config) Thư mục tự động tạo chứa Vector db.
├── main.py             # Entry point để chạy Uvicorn, init Database
├── docker-compose.yml  # Dựng nhanh PostgreSQL + PostGIS (Pgvector) 
└── requirements.txt    # Danh sách packages cài đặt
```

## 🛠 Luồng Xử Lý (Data Flow Dễ Hiểu)

Khi có một API gọi đến (`VD: POST /api/v1/chat`), luồng đi sẽ như sau:
1. **API Router (`app/api/endpoints`)**: Node đầu tiên hứng request. Nó dựa vào class ở `app/schemas` để bắt lỗi nhập sai đầu vào.
2. **Services (`app/services`)**: File router không xử lý thuật toán! Nó gọi một hàm trong thư mục Service. Service sẽ tiếp nhận, tiến hành băm text, vectorize.
3. **Database (`app/models`)**: Nếu Service cần tra lịch sử hay nhét log, nó sẽ dùng model hệ thống SQLAlchemy tại đây và trỏ xuống PostgreSQL.
4. **Trả kết quả**: Mô hình (Load từ `model_loader.py`) đưa ra đáp án, gửi lại cho Service, và API ném về FE thông qua base format tại `app/core/common/interceptor.py`.

## ✍️ Bí kíp Maintain & Code Hằng Ngày

### 1. Cách Thêm Một Bảng Database Mới
- Mở thư mục `app/models/` và tạo 1 file `[tên_bảng].py` chứa class SQLAlchemy kế thừa từ `RagBase`.
- File `main.py` có đoạn `RagBase.metadata.create_all()` nên khi bạn start server mới, DB tự động sinh bảng nến chưa có.

### 2. Cách Tạo Môđun Tính Năng Mới
- **B1**: Tạo Pydantic Schema ở `app/schemas/` kiểm soát đầu vào/ra.
- **B2**: Code Business Logic thao tác DB & Module AI ở thư mục `app/services/`.
- **B3**: Tạo Method Controller nhận Route bằng FastAPI tại `app/api/endpoints/`.
- **B4**: Quăng file api script đó vào hàm `router.include_router` trong `app/api/routes.py`.

### 3. Đổi & Upgrade Mô Hình Sinh Văn Bản (LLM) / Embedding Model
- Mở `app/services/model_loader.py` để tìm vị trí load.
- Lưu ý hệ thống định dạng AI dùng `.gguf`. Bạn phải tự tạo folder `app/models_weights/` rồi bỏ cục weights đó vào, sau đó thay lại tham số môi trường trong `.env`.

## ⚙️ Clone code về máy tính cá nhân để chạy thử:

1. Đảm bảo có Python (ưu tiên >3.10) và **C++ Build Tools** (nếu bạn xài windows, phải có C++ build tools để nó compile pakage AI như `llama-cpp-python`).
2. Mở cmd trong project vừa clone, tạo venv:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate      # Windows
   # source venv/bin/activate   # Linux/macOS
   ```
3. Cài hàng loạt packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Tạo folder thiếu sót trong repo:
   ```bash
   mkdir data\raw_data
   mkdir app\models_weights
   ```
5. Chạy nhanh con PostgreSQL đã cài sẵn Pgvector:
   ```bash
   docker-compose up -d
   ```
6. Copy nội dung file `.env.development` (hoặc tạo file mới) chuyển qua tên `.env`, sửa lại `RAG_DB_URL` nếu cần thiết.
7. Kickstart FastAPI:
   ```bash
   python main.py
   ```
   > 🚀 Chạy thành công sẽ hiển thị ở `http://localhost:8000`. Swagger API test ở `http://localhost:8000/docs`.

---
Chúc bạn may mắn khi làm chủ kiến trúc mã nguồn này. Hệ thống handler lỗi chuẩn đã được nằm sắn trong `app/core/common/interceptor.py`, nếu lỗi nội bộ phát sinh hãy cắm log ở đây.
