import logging
import os

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models import RagConfig, AIModel
from app.core.config import settings
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
        """Seed AI models and RAG configuration from JSON file."""
        import json
        seed_file = os.path.join(BASE_DIR, "seeds", "ai_model_seed.json")
        
        if not os.path.exists(seed_file):
            logger.warning(f"Không tìm thấy file seed: {seed_file}")
            return

        try:
            with open(seed_file, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc file seed: {e}")
            return

        default_model = None

        # 1. Seed/Sync AI Models
        for item in seed_data:
            model_name = item.get("name")
            is_default = item.pop("is_default", False) # Lấy ra và xóa để không đưa vào constructor AIModel

            llm = db.query(AIModel).filter(AIModel.name == model_name).first()
            
            if not llm:
                logger.info(f"Seeding AI Model mới: {model_name}")
                llm = AIModel(**item)
                db.add(llm)
                db.flush() # Để có ID
            else:
                # Update nếu đã tồn tại để đồng bộ cấu hình mới nhất từ file seed
                for key, value in item.items():
                    setattr(llm, key, value)
                logger.info(f"Đã cập nhật cấu hình cho Model: {model_name}")

            if is_default:
                default_model = llm

        db.commit()

        # 2. Seed/Sync RagConfig mặc định
        config = db.query(RagConfig).first()
        if not config:
            logger.info("Bắt đầu khởi tạo cấu hình RAG mặc định...")
            default_config = RagConfig(
                name="Cấu hình y khoa mặc định",
                default_llm_id=default_model.id if default_model else None,
                top_k=5,
                threshold=0.4,
                temperature=0.1,
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
        else:
            # Luôn cập nhật default LLM từ file seed nếu có đánh dấu default
            if default_model:
                config.default_llm_id = default_model.id
        
        db.commit()
        logger.info("Hoàn tất quá trình đồng bộ dữ liệu Seed.")
        return config