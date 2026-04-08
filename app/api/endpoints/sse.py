from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.services.sse_service import SSEService
import uuid

router = APIRouter()

@router.get("/stream/{client_id}", summary="Kết nối SSE Stream", tags=["SSE"])
async def sse_endpoint(request: Request, client_id: str):
    """
    Endpoint duy trì kết nối SSE. FE sẽ kết nối vào đây qua EventSource.
    """
    return StreamingResponse(
        SSEService.subscribe(client_id),
        media_type="text/event-stream"
    )

@router.post("/test-event", summary="Test SSE Event (Dành cho Dev)", tags=["SSE"])
async def test_sse_event(client_id: str, message: str):
    """Bắn thử một log message để kiểm tra kết nối."""
    await SSEService.send_log(client_id, f"Test log: {message}", progress=50)
    await SSEService.send_alert(client_id, "Thông báo thử nghiệm", "SSE hoạt động tốt!")
    return {"message": "Event sent"}
