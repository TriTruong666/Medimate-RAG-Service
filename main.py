import sys
import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.core.db.rag_database import SessionLocal
from fastapi import FastAPI
from app.services.rag_config_service import RagConfigService
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.common.interceptor import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    APIResponse,
)
from app.core.db.rag_database import RagBase, rag_engine

# Schemas
from app.models import Document, Embedding, RagConfig, Collection

# API routes
from app.api.routes import router as api_router

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        RagConfigService.seed_config(db)
    finally:
        db.close()
    yield

def get_application() -> FastAPI:
    # Config app
    app = FastAPI(
        title=f"Medimate RAG Services - {settings.AUTHOR_NAME}",
        version=settings.APP_VERSION,
        docs_url="/docs",
        lifespan=lifespan,
    )
    # Config CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # mốt nhớ đổi domain riel
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Thêm handler http exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    try:
        with rag_engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()  # Nhớ commit để lưu thay đổi
            logging.info("Đã kích hoạt Extension pgvector")
        RagBase.metadata.create_all(bind=rag_engine)
        from app.core.db.rag_database import setup_database
        setup_database()
        logging.info(f"Đã kết nối Database, khởi tạo thành công các bảng và indexes")
    except Exception as e:
        logger.error(f"Kết nối đến Database thất bại: {e}")

    return app


# Khởi tạo app
app = get_application()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    openapi_schema["security"] = [{"HTTPBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Gắn router API
app.include_router(api_router, prefix="/api/v1")

@app.get("/system/health", tags=["Health Check"])
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
