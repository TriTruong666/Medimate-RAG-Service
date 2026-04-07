import logging
import os

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models import RagConfig
from fastapi import HTTPException, status

from app.schemas.rag_config import RagConfigCreate, RagConfigUpdate

BASE_DIR = os.getcwd()
logger = logging.getLogger(__name__)


class RagConfigService:
    @staticmethod
    def list_configs(db: Session):
        return db.query(RagConfig).order_by(RagConfig.id.desc()).all()

    @staticmethod
    def get_config_by_id(db: Session, config_id: int):
        config = db.query(RagConfig).filter(RagConfig.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy cấu hình RAG"
            )
        return config

    @staticmethod
    def create_config(db: Session, payload: RagConfigCreate):
        try:
            config = RagConfig(**payload.model_dump())
            db.add(config)
            db.commit()
            db.refresh(config)
            return config
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Lỗi DB khi tạo cấu hình")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi DB khi tạo cấu hình",
            )

    @staticmethod
    def update_config(db: Session, config_id: int, payload: RagConfigUpdate):
        config = RagConfigService.get_config_by_id(db, config_id)
        updated_data = payload.model_dump(exclude_unset=True)

        if not updated_data:
            return config
        try:
            for field, value in updated_data.items():
                setattr(config, field, value)
            db.commit()
            db.refresh(config)
            return config
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Lỗi DB khi cập nhật cấu hình")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi DB khi cập nhật cấu hình",
            )

    @staticmethod
    def delete_config(db: Session, config_id: int):
        config = RagConfigService.get_config_by_id(db, config_id)
        try:
            db.delete(config)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Lỗi DB khi xoá cấu hình")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi DB khi xoá cấu hình",
            )

    
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
            logger.info("Bắt đầu seed cấu hình RAG mặc định...")
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
        
        logger.info("Cấu hình RAG đã tồn tại, bỏ qua bước seed.")
        return config