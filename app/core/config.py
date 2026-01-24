import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.getcwd()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Meditate RAG Service"
    AUTHOR_NAME: str = "TriTruong666"
    MODEL_PATH: str = os.path.join(
        BASE_DIR, "app", "models_weights", "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    )

    APP_VERSION: str = "1.0.0"

    APP_PORT: int = os.getenv("APP_PORT")

    APP_HOST: str = os.getenv("APP_HOST")

    RAW_UPLOAD_PATH: str = os.path.join(BASE_DIR, "data", "raw_data")

    CHROMA_DB_DIR: str = os.path.join(BASE_DIR, "app", "data", "chroma_db")

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    RAG_DB_URL: str = os.getenv("RAG_DB_URL")


settings = Settings()
