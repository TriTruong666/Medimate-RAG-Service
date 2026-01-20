import os
from pydantic_settings import BaseSettings

# Lấy đường dẫn thư mục gốc (D:\Dev\Python\rag)
BASE_DIR = os.getcwd()

class Settings(BaseSettings):
    PROJECT_NAME: str = "MPF RAG Service"
    
    # --- SỬA LỖI Ở ĐÂY: Dùng dấu phẩy (,) thay vì gạch chéo (\) ---
    
    # Đường dẫn đến file Model
    # Python sẽ tự ghép thành: D:\Dev\Python\rag\app\models_weights\qwen2.5...
    MODEL_PATH: str = os.path.join(BASE_DIR, "app", "models_weights", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
    
    # Đường dẫn đến thư mục Upload
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "app", "data", "uploads")
    
    # Đường dẫn đến thư mục Vector DB
    VECTOR_DB_DIR: str = os.path.join(BASE_DIR, "app", "data", "vector_store")
    
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

settings = Settings()

# --- CODE DEBUG (GIỮ NGUYÊN ĐỂ KIỂM TRA) ---
print("\n" + "="*40)
print("--- KIỂM TRA ĐƯỜNG DẪN (DEBUG) ---")
print(f"📂 Thư mục gốc: {BASE_DIR}")
print(f"🎯 Đang tìm Model tại: {settings.MODEL_PATH}")
print(f"👉 Kết quả: {'✅ TÌM THẤY' if os.path.exists(settings.MODEL_PATH) else '❌ KHÔNG TÌM THẤY (Sai đường dẫn)'}")
print("="*40 + "\n")