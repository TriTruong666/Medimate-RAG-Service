import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime


class SSEService:
    """
    Dịch vụ quản lý Server-Sent Events (SSE).
    Hỗ trợ bắn logs quá trình xử lý và thông báo (Alert) cho phía Client.
    """

    # Lưu trữ các queue cho từng client. Key có thể là user_id hoặc connection_id.
    _queues: Dict[str, asyncio.Queue] = {}

    @classmethod
    async def subscribe(cls, client_id: str):
        """Đăng ký một client mới nhận stream."""
        queue = asyncio.Queue()
        cls._queues[client_id] = queue
        try:
            while True:
                try:
                    # Chờ dữ liệu từ queue hoặc timeout sau 30s để gửi heartbeat
                    data = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield data
                except asyncio.TimeoutError:
                    # Gửi heartbeat (comment trong giao thức SSE) để giữ kết nối
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            # Xử lý khi client ngắt kết nối
            if client_id in cls._queues:
                del cls._queues[client_id]
            raise

    @classmethod
    async def push_event(cls, client_id: str, event_type: str, data: Any):
        """
        Bắn một event đến một client cụ thể.
        Nếu client_id là 'all', bắn cho toàn bộ client đang kết nối.
        """
        message = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "payload": data,
        }

        formatted_message = f"data: {json.dumps(message)}\n\n"

        if client_id == "all":
            for q in cls._queues.values():
                await q.put(formatted_message)
        elif client_id in cls._queues:
            await cls._queues[client_id].put(formatted_message)

    @classmethod
    async def send_log(
        cls, client_id: str, message: str, status: str = "info", progress: int = None
    ):
        """Template cho việc bắn log quá trình xử lý."""
        payload = {
            "message": message,
            "status": status,  # info, warning, success, error
            "progress": progress,
        }
        await cls.push_event(client_id, "process_log", payload)

    @classmethod
    async def send_alert(
        cls, client_id: str, title: str, body: str, alert_type: str = "info"
    ):
        """Template cho việc bắn thông báo nổi (Alert)."""
        payload = {
            "title": title,
            "body": body,
            "alert_type": alert_type,  # info, success, warning, error
        }
        await cls.push_event(client_id, "alert", payload)
