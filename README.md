# Medimate RAG Service

---

## Yêu cầu hệ thống (Prerequisites)

Trước khi bắt đầu, đảm bảo mày đã cài:
  **C++ Build Tools** (RẤT QUAN TRỌNG):
    * Tải [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
    * Khi cài đặt, tích chọn **"Desktop development with C++"**.

---

## Bước 1: Setup dự án

### 1.1. Cài môi trường virtual

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate
```

### 1.2 Cài thư các thư viện

```bash
pip install -r ./requirements.txt
```

### 1.3 Tạo các thư mục còn thiếu


---

## Bước 2: Tải model AI (.gguf)
  Dự án sử dụng model định dạng `.gguf` để chạy nhẹ trên CPU/RAM thường.

    
  ### 2.1 Tải Model Qwen 2.5 (Khuyên dùng) hoặc Llama 3:
  - <strong>Máy yếu (Laptop văn phòng, 8GB RAM)</strong>: [Model AI Qwen 1.5B (Q4_K_M)](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/main)
  - <strong>Máy khoẻ (PC, 16GB RAM)</strong>: [Model AI Qwen 7B (Q4_K_M)](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/main)

  ### 2.2 Tạo thư mục `models_weights` trong folder app:

  ```structure
    /app
        /models_weights
            <Bỏ file .gguf vừa tải vào đây>
  ```

---

## Bước 3: Chuẩn bị data

1. Vào thư mục `data`
1. Tạo thư mục tên là `uploads` (nếu chưa có).
1. **Copy các file tài liệu** mà mày muốn nó học.
    - Hỗ trợ tốt nhất: `.txt`, `.pdf`, `.docx`

```structure
    /data
        /uploads
            du_an_A.pdf
            huong_dan.txt

```

---

## Bước 4: Chạy dự án

Tại thư mục gốc (đang bật `venv`), chạy lệnh:

```script
python main.py
```

**Chúc tụi mày thành công**