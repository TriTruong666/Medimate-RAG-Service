from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.services.sse_service import SSEService
from app.core.auth.deps import RequireAdmin, RequireAdminOrUser
import uuid

router = APIRouter()


@router.get("/stream/{client_id}", summary="Kết nối SSE Stream", tags=["SSE"], dependencies=[RequireAdminOrUser])
async def sse_endpoint(request: Request, client_id: str):
    """
    Endpoint duy trì kết nối SSE. FE sẽ kết nối vào đây qua EventSource.
    """
    return StreamingResponse(
        SSEService.subscribe(client_id), media_type="text/event-stream"
    )


@router.post("/test-event", summary="Test SSE Event (Dành cho Dev)", tags=["SSE"], dependencies=[RequireAdmin])
async def test_sse_event(client_id: str, message: str):
    """Bắn thử một log message để kiểm tra kết nối."""
    await SSEService.send_log(client_id, f"Test log: {message}", progress=50)
    await SSEService.send_alert(client_id, "Thông báo thử nghiệm", "SSE hoạt động tốt!")
    return {"message": "Event sent"}


@router.post(
    "/send-notification", summary="Gửi thông báo trực tiếp qua SSE", tags=["SSE"], dependencies=[RequireAdmin]
)
async def send_notification(
    client_id: str, title: str, message: str, alert_type: str = "info"
):
    """
    API dùng để bắn ngay một thông báo (Alert) tới client cụ thể mà không cần lưu DB.
    - client_id: ID của người nhận (hoặc 'all' để gửi tất cả)
    - alert_type: info, success, warning, error
    """
    from app.core.common.interceptor import APIResponse

    await SSEService.send_alert(client_id, title, message, alert_type)
    return APIResponse.success(message="Thông báo đã được gửi.")
