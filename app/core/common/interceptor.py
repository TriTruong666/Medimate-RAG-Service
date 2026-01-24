import logging
from typing import Any, Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Setup logger để ghi lại lỗi hệ thống (nếu có)
logger = logging.getLogger("uvicorn.error")


class APIResponse:
    """
    Class này giúp chuẩn hóa mọi response trả về theo 1 format duy nhất.
    Frontend sẽ rất thích điều này!
    """

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
                "data": data,
            },
        )

    @staticmethod
    def error(
        message: str, status_code: int = status.HTTP_400_BAD_REQUEST, errors: Any = None
    ):
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "code": status_code,
                "message": message,
                "errors": errors,  # Chi tiết lỗi (nếu có)
                "data": None,
            },
        )


# --- CÁC HANDLER ĐỂ INTERCEPT LỖI TỰ ĐỘNG ---


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Bắt tất cả các lỗi HTTPException(status_code=...) mà ông raise trong code.
    Ví dụ: raise HTTPException(404, detail="Không tìm thấy file")
    """
    return APIResponse.error(message=str(exc.detail), status_code=exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Bắt lỗi dữ liệu đầu vào (Pydantic).
    Ví dụ: User gửi thiếu trường 'doc_name' hoặc sai kiểu dữ liệu.
    """
    # Format lại lỗi của Pydantic cho dễ đọc
    errors = []
    for error in exc.errors():
        field = ".".join(
            str(x) for x in error["loc"]
        )  # Lấy tên trường bị lỗi (body.doc_name)
        msg = error["msg"]
        errors.append(f"{field}: {msg}")

    return APIResponse.error(
        message="Dữ liệu đầu vào không hợp lệ",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        errors=errors,
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Bắt tất cả các lỗi còn lại (Lỗi 500 - Server Error).
    Ví dụ: Code bị bug, chia cho 0, database mất kết nối...
    """
    # Ghi log để dev biết đường sửa
    logger.error(f"Lỗi không mong muốn: {exc}", exc_info=True)

    return APIResponse.error(
        message="Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        errors=str(exc),  # Môi trường Dev thì để cái này, Prod thì nên ẩn đi
    )
