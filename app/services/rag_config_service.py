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
                embedding_model="BAAI/bge-m3",
                llm_model=os.path.join(BASE_DIR, "app", "models_weights", "qwen2.5-1.5b-instruct-q4_k_m.gguf"),
                chunk_size=1024,
                chunk_overlap=150,
                top_k=5,
                temperature=0.1,
                max_tokens=1024,
                context_window=32768, # BGE-M3 và Qwen hỗ trợ context window tốt hơn
                prompt_template=(
                    "Dựa vào thông tin ngữ cảnh bên dưới, hãy trả lời câu hỏi bằng Tiếng Việt một cách chính xác nhất (đặc biệt là các chỉ số y khoa).\n"
                    "BẮT BUỘC TRÍCH DẪN: Mỗi thông tin bạn trích dẫn phải ghi rõ nguồn theo định dạng [Nguồn: <tên tài liệu>].\n\n"
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