# SSE Implementation Skill (Server-Sent Events)

Tài liệu này hướng dẫn cách sử dụng `SSEService` để bắn thông báo và logs thời gian thực cho Client trong các tác vụ chạy nền (Background Tasks) hoặc tác vụ tốn thời gian.

## 1. Kiến trúc luồng đi (Flow)

1.  **Client:** Kết nối vào `GET /api/v1/sse/stream/{client_id}`.
2.  **API:** Nhận request xử lý (ví dụ: Bulk Ingest), ngay lập tức trả về `202 Accepted` kèm `client_id`.
3.  **Hệ thống (Background Task):** Thực thi logic, đồng thời gọi `SSEService` để đẩy trạng thái về Front-end.
4.  **Client:** Nhận data qua `EventSource` và cập nhật UI (Progress bar, Notifications).

## 2. Cách sử dụng trong Code

### Bước 1: Khai báo Background Task trong Endpoint
Cần trả về response nhanh nhất có thể để tránh timeout.

```python
from fastapi import BackgroundTasks
from app.services.sse_service import SSEService

@router.post("/process-data")
async def process_data(client_id: str, background_tasks: BackgroundTasks):
    # Trả về 202 ngay lập tức
    background_tasks.add_task(my_long_service, client_id)
    return APIResponse.success(message="Đang xử lý trong nền...", status_code=202)
```

### Bước 2: Bắn Logs và Alerts từ Service
Dùng `SSEService` để cập nhật tiến độ.

```python
from app.services.sse_service import SSEService

async def my_long_service(client_id: str):
    # 1. Bắt đầu xử lý
    await SSEService.send_log(client_id, "Bắt đầu nạp dữ liệu...", progress=0)
    
    # 2. Xử lý từng phần
    for i in range(1, 11):
        await asyncio.sleep(1) # Giả lập task
        await SSEService.send_log(client_id, f"Đang xử lý phần {i}/10", progress=i*10)
    
    # 3. Hoàn thành và bắn Alert
    await SSEService.send_alert(
        client_id, 
        title="Xử lý thành công", 
        body="Toàn bộ tài liệu đã được nạp xong!", 
        alert_type="success"
    )
```

## 3. Các loại sự kiện hỗ trợ

*   **`process_log`**: Dùng cho thanh tiến độ hoặc log terminal trên UI. 
    - Payload: `{ "message": str, "status": str, "progress": int }`
*   **`alert`**: Dùng cho thông báo dạng Toast/Pop-up.
    - Payload: `{ "title": str, "body": str, "alert_type": str }`

## 4. Lưu ý quan trọng
- SSE là kết nối một chiều (Server -> Client).
- Phải đảm bảo `client_id` được truyền chính xác từ FE xuống BE để bắn đúng người.
- Trong môi trường Production (Nginx), cần cấu hình `proxy_buffering off` và `proxy_cache off` để SSE hoạt động mượt mà.
