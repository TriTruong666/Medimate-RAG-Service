import logging
from typing import Any, Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("uvicorn.error")


class APIResponse:

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Thành công",
        status_code: int = status.HTTP_200_OK,
    ):
        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "code": status_code,
                "message": message,
                "data": jsonable_encoder(data),
            },
        )

    @staticmethod
    def error(
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Any = None,
        headers: dict[str, str] | None = None,
    ):
        return JSONResponse(
            status_code=status_code,
            headers=headers,
            content={
                "success": False,
                "code": status_code,
                "message": message,
                "errors": errors,  
                "data": None,
            },
        )




async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Bắt tất cả các lỗi HTTPException(status_code=...) mà ông raise trong code.
    Ví dụ: raise HTTPException(404, detail="Không tìm thấy file")
    """
    headers = dict(exc.headers or {})
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS and "Retry-After" not in headers:
        retry_after = getattr(request.state, "retry_after", None)
        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)

    message = str(exc.detail)
    errors = None
    if isinstance(exc.detail, dict):
        message = str(exc.detail.get("message", message))
        extra_fields = {k: v for k, v in exc.detail.items() if k != "message"}
        errors = extra_fields or None
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        retry_after = getattr(request.state, "retry_after", None)
        if retry_after is not None:
            errors = {"retry_after_seconds": retry_after}

    return APIResponse.error(
        message=message,
        status_code=exc.status_code,
        errors=errors,
        headers=headers or None,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Bắt lỗi dữ liệu đầu vào (Pydantic).
    Ví dụ: User gửi thiếu trường 'doc_name' hoặc sai kiểu dữ liệu.
    """
    errors = []
    for error in exc.errors():
        field = ".".join(
            str(x) for x in error["loc"]
        ) 
        msg = error["msg"]
        errors.append(f"{field}: {msg}")

    return APIResponse.error(
        message="Dữ liệu đầu vào không hợp lệ",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        errors=errors,
    )


async def general_exception_handler(request: Request, exc: Exception):
    # Ghi log để dev biết đường sửa
    logger.error(f"Lỗi không mong muốn: {exc}", exc_info=True)

    return APIResponse.error(
        message="Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        errors=str(exc),  # Dev thì để, còn Prod thì nhớ bỏ
    )
