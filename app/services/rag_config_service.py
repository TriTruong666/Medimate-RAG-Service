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
        import json
        seed_file = os.path.join(BASE_DIR, "seeds", "ai_model_seed.json")
        
        if not os.path.exists(seed_file):
            logger.warning(f"Không tìm thấy file seed: {seed_file}")
            return

        try:
            with open(seed_file, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
            
            default_model = None

            # 1. Seed/Sync AI Models
            for item in seed_data:
                # Copy dữ liệu để tránh làm hỏng dict gốc
                data = item.copy()
                model_name = data.get("name")
                is_default = data.pop("is_default", False)

                # Tìm model cũ
                llm = db.query(AIModel).filter(AIModel.name == model_name).first()
                
                try:
                    if not llm:
                        logger.info(f"Seeding AI Model mới: {model_name}")
                        llm = AIModel(**data)
                        db.add(llm)
                    else:
                        # Update nếu đã tồn tại
                        for key, value in data.items():
                            setattr(llm, key, value)
                        logger.info(f"Đã cập nhật cấu hình cho Model: {model_name}")
                    
                    # Flush riêng cho từng model để bắt lỗi ngay nếu trùng
                    db.flush() 
                    
                except SQLAlchemyError as e:
                    db.rollback() # Quan trọng: Rollback ngay nếu trùng
                    logger.error(f"Lỗi khi seed model {model_name}: {e}")
                    # Lấy lại instance sau khi rollback để xử lý tiếp
                    llm = db.query(AIModel).filter(AIModel.name == model_name).first()

                if is_default:
                    default_model = llm

            # 2. Seed/Sync RagConfig mặc định
            config = db.query(RagConfig).first()
            if not config:
                logger.info("Bắt đầu khởi tạo cấu hình RAG mặc định...")
                config = RagConfig(
                    name="Cấu hình y khoa mặc định",
                    default_llm_id=default_model.id if default_model else None,
                    top_k=5,
                    threshold=0.4,
                    temperature=0.1,
                    prompt_template="..." # Giữ nguyên template của bạn
                )
                db.add(config)
            else:
                if default_model:
                    config.default_llm_id = default_model.id
            
            db.commit()
            logger.info("Hoàn tất quá trình đồng bộ dữ liệu Seed.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"LỖI NGHIÊM TRỌNG TRONG SEED CONFIG: {e}")
