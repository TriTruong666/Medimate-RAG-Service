import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local", override=True)

BASE_DIR = os.getcwd()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Meditate RAG Service"
    AUTHOR_NAME: str = "TriTruong666"

    APP_VERSION: str = "1.0.0"

    APP_PORT: int = os.getenv("APP_PORT")

    APP_HOST: str = os.getenv("APP_HOST")

    RAW_UPLOAD_PATH: str = os.path.join(BASE_DIR, "data", "raw_data")

    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"

    RAG_DB_URL: str = os.getenv("RAG_DB_URL")

    POSTGRES_DB: str = os.getenv("POSTGRES_DB")

    POSTGRES_USER: str = os.getenv("POSTGRES_USER")

    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER")

    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")

    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT"))

    CHAT_RATE_LIMIT_MAX_REQUESTS: int = int(
        os.getenv("CHAT_RATE_LIMIT_MAX_REQUESTS", "10")
    )
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = int(
        os.getenv("CHAT_RATE_LIMIT_WINDOW_SECONDS", "60")
    )
    DOC_PROCESS_RATE_LIMIT_MAX_REQUESTS: int = int(
        os.getenv("DOC_PROCESS_RATE_LIMIT_MAX_REQUESTS", "5")
    )
    DOC_PROCESS_RATE_LIMIT_WINDOW_SECONDS: int = int(
        os.getenv("DOC_PROCESS_RATE_LIMIT_WINDOW_SECONDS", "60")
    )

    # Auth service configuration
    AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER")
    AUTH_GRPC_TARGET: str = os.getenv("AUTH_GRPC_TARGET")
    AUTH_GRPC_TIMEOUT_SECONDS: float = float(
        os.getenv("AUTH_GRPC_TIMEOUT_SECONDS", "2.0")
    )
    # Quan trọng chỉ reset DB khi dev, prod khi cần thiết và thêm bảng hoặc sửa bảng
    IS_RESET_DB: bool = os.getenv("IS_RESET_DB", "False").lower() in ("true", "1", "t")


settings = Settings()

# Ensure directories exist
os.makedirs(settings.RAW_UPLOAD_PATH, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "app", "models_weights"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "seeds"), exist_ok=True)
