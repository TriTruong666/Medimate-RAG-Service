import os
from pydantic_settings import BaseSettings

BASE_DIR = os.getcwd()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Meditate RAG Service"
    MODEL_PATH: str = os.path.join(
        BASE_DIR, "app", "models_weights", "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    )

    UPLOAD_DIR: str = os.path.join(BASE_DIR, "app", "data", "uploads")

    VECTOR_DB_DIR: str = os.path.join(BASE_DIR, "app", "data", "vector_store")

    CHROMA_DB_DIR: str = os.path.join(BASE_DIR, "app", "data", "chroma_db")

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"


settings = Settings()
