import sys
import os
import logging
import uvicorn
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.common.interceptor import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    APIResponse,
)
from app.core.db.rag_database import RagBase, rag_engine

# Schemas
from app.schemas import Document, Embedding, MobilePackage, RagConfig

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.getcwd())


def print_banner():
    logo = r"""
███╗   ███╗███████╗██████╗ ██╗███╗   ███╗ █████╗ ████████╗███████╗
████╗ ████║██╔════╝██╔══██╗██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║█████╗  ██║  ██║██║██╔████╔██║███████║   ██║   █████╗  
██║╚██╔╝██║██╔══╝  ██║  ██║██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║███████╗██████╔╝██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

██████╗  █████╗  ██████╗     ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗
██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝
██████╔╝███████║██║  ███╗    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  
██╔══██╗██╔══██║██║   ██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  
██║  ██║██║  ██║╚██████╔╝    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝
    """
    print(logo)


def get_application() -> FastAPI:
    # Config app
    app = FastAPI(
        title=f"Medimate RAG Services - {settings.AUTHOR_NAME}",
        version=settings.APP_VERSION,
        docs_url="/docs",
    )
    # Config CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # mốt nhớ đổi domain riel
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Thêm pipeline http exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    try:
        with rag_engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()  # Nhớ commit để lưu thay đổi
            logging.info("Đã kích hoạt Extension pgvector")
        RagBase.metadata.create_all(bind=rag_engine)
        logging.info(f"Đã kết nối Database, khởi tạo thành công các bảng")
    except Exception as e:
        logger.error(f"Kết nối đến Database thất bại: {e}")

    return app


# Khởi tạo app
app = get_application()


@app.get("/health", tags=["Health Check"])
async def root():
    return APIResponse.success(
        message="Server đang hoạt động bình thường",
        data={"version": settings.APP_VERSION, "author": settings.AUTHOR_NAME},
    )


def main():
    print_banner()

    uvicorn.run("main:app", port=settings.APP_PORT, host=settings.APP_HOST, reload=True)


if __name__ == "__main__":
    main()
