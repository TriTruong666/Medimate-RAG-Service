from sqlalchemy.orm import Session
from app.models import RagConfig
from fastapi import HTTPException
import os

BASE_DIR = os.getcwd()
class RagConfigService:
    @staticmethod
    def get_rag_config(db: Session):
        config = db.query(RagConfig).first()
        if not config:
           raise HTTPException(
                status_code=404, 
                detail=f"Chưa có cấu hình RAG trong hệ thống!"
            )
        return config


    @staticmethod
    def seed_config(db: Session):
        config = db.query(RagConfig).first()
        
        if not config:
            print("Bắt đầu seed cấu hình RAG mặc định...")
            default_config = RagConfig(
                embedding_model="sentence-transformers/all-MiniLM-L6-v2",
                llm_model=os.path.join(BASE_DIR, "app", "models_weights", "qwen2.5-1.5b-instruct-q4_k_m.gguf"),
                chunk_size=512,
                chunk_overlap=50,
                top_k=5,
                temperature=0.1,
                max_tokens=512,
                context_window=3900,
                prompt_template=(
        "Dựa vào thông tin ngữ cảnh bên dưới, hãy trả lời câu hỏi bằng Tiếng Việt.\n"
        "Nếu thông tin không có trong ngữ cảnh, hãy nói 'Tôi không tìm thấy thông tin'.\n"
        "---------------------\n"
        "Ngữ cảnh:\n"
        "{context_str}\n"
        "---------------------\n"
        "Câu hỏi: {query_str}\n"
        "Trả lời:"
    )
            )
            db.add(default_config)
            db.commit()
            db.refresh(default_config)
            return default_config
        
        print("Cấu hình RAG đã tồn tại, bỏ qua bước seed.")
        return config