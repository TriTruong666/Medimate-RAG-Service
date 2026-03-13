import math
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, Request, status
from app.core.config import settings


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._storage: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _cleanup(self, bucket: Deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def check(self, request: Request, route_key: str) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, route_key)
        now = time.monotonic()

        with self._lock:
            bucket = self._storage[key]
            self._cleanup(bucket, now)

            if len(bucket) >= self.max_requests:
                oldest = bucket[0]
                retry_after = max(1, math.ceil(self.window_seconds - (now - oldest)))
                request.state.retry_after = retry_after
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": (
                            f"Quá nhiều yêu cầu. Giới hạn {self.max_requests} lần/"
                            f"{self.window_seconds} giây."
                        ),
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)


chat_completion_limiter = InMemoryRateLimiter(
    max_requests=settings.CHAT_RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.CHAT_RATE_LIMIT_WINDOW_SECONDS,
)
document_process_limiter = InMemoryRateLimiter(
    max_requests=settings.DOC_PROCESS_RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.DOC_PROCESS_RATE_LIMIT_WINDOW_SECONDS,
)


def rate_limit_chat_completion(request: Request) -> None:
    chat_completion_limiter.check(request, "chat_completion")


def rate_limit_document_process(request: Request) -> None:
    document_process_limiter.check(request, "document_process")
