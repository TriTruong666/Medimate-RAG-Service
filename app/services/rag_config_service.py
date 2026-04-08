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
            raise HTTPException(status_code=404, detail=f"Không tìm thấy cấu hình RAG")
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
                status_code=404, detail=f"Chưa có cấu hình RAG trong hệ thống!"
            )
        return config

    @staticmethod
    def seed_config(db: Session):
        import json

        model_seed_file = os.path.join(BASE_DIR, "seeds", "ai_model_seed.json")
        config_seed_file = os.path.join(BASE_DIR, "seeds", "rag_config_seed.json")

        try:
            default_model_id = None

            # 1. Seed/Sync AI Models từ file ai_model_seed.json
            if os.path.exists(model_seed_file):
                with open(model_seed_file, "r", encoding="utf-8") as f:
                    model_seed_data = json.load(f)

                for item in model_seed_data:
                    data = item.copy()
                    model_name = data.get("name")
                    is_default = data.pop("is_default", False)

                    llm = db.query(AIModel).filter(AIModel.name == model_name).first()

                    if not llm:
                        logger.info(f"Seeding AI Model mới: {model_name}")
                        llm = AIModel(**data)
                        db.add(llm)
                        db.flush()
                    else:
                        for key, value in data.items():
                            setattr(llm, key, value)
                        db.flush()

                    if is_default:
                        default_model_id = llm.id
            else:
                logger.warning(f"Không tìm thấy file seed AI Model: {model_seed_file}")

            # 2. Seed/Sync RagConfig từ file rag_config_seed.json
            if os.path.exists(config_seed_file):
                with open(config_seed_file, "r", encoding="utf-8") as f:
                    config_seed_data = json.load(f)

                config = db.query(RagConfig).first()
                if not config:
                    logger.info("Bắt đầu khởi tạo cấu hình RAG mặc định từ JSON...")
                    config = RagConfig(
                        **config_seed_data, default_llm_id=default_model_id
                    )
                    db.add(config)
                else:
                    # Cập nhật nếu đã tồn tại
                    for key, value in config_seed_data.items():
                        setattr(config, key, value)
                    if default_model_id:
                        config.default_llm_id = default_model_id
                    logger.info("Đã cập nhật cấu hình RAG từ file JSON.")
            else:
                logger.warning(
                    f"Không tìm thấy file seed RagConfig: {config_seed_file}"
                )

            db.commit()
            logger.info("Hoàn tất quá trình đồng bộ dữ liệu Seed.")

        except Exception as e:
            db.rollback()
            logger.error(f"LỖI NGHIÊM TRỌNG TRONG SEED CONFIG: {e}")
