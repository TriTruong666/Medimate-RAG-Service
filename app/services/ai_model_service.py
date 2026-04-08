import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.ai_model import AIModel
from app.schemas.ai_model import AIModelCreate, AIModelUpdate
from uuid import UUID

logger = logging.getLogger(__name__)


class AIModelService:
    @staticmethod
    def get_list(db: Session, skip: int = 0, limit: int = 100):
        """Lấy danh sách tất cả các AI Model."""
        return (
            db.query(AIModel)
            .order_by(AIModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, model_id: UUID):
        """Lấy thông tin AI Model theo ID."""
        model = db.query(AIModel).filter(AIModel.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy AI Model này",
            )
        return model

    @staticmethod
    def create(db: Session, payload: AIModelCreate):
        """Tạo một AI Model mới."""
        # Kiểm tra trùng tên
        exist_model = db.query(AIModel).filter(AIModel.name == payload.name).first()
        if exist_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model với tên '{payload.name}' đã tồn tại",
            )

        try:
            model = AIModel(**payload.model_dump())
            db.add(model)
            db.commit()
            db.refresh(model)
            return model
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Lỗi DB khi tạo AI Model")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi trong quá trình tạo AI Model. Thuộc tính hoặc cấu hình JSON có thể không hợp lệ.",
            )

    @staticmethod
    def update(db: Session, model_id: UUID, payload: AIModelUpdate):
        """Cập nhật thông tin AI Model."""
        model = AIModelService.get_by_id(db, model_id)

        updated_data = payload.model_dump(exclude_unset=True)
        if not updated_data:
            return model

        # Kiểm tra trùng tên nếu có cập nhật tên
        if "name" in updated_data and updated_data["name"] != model.name:
            exist_model = (
                db.query(AIModel).filter(AIModel.name == updated_data["name"]).first()
            )
            if exist_model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model với tên '{updated_data['name']}' đã tồn tại",
                )

        try:
            for field, value in updated_data.items():
                setattr(model, field, value)
            db.commit()
            db.refresh(model)
            return model
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Lỗi DB khi cập nhật AI Model")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi xử lý Database cập nhật AI Model",
            )

    @staticmethod
    def delete(db: Session, model_id: UUID):
        """Xoá một AI Model."""
        model = AIModelService.get_by_id(db, model_id)
        try:
            db.delete(model)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Lỗi DB khi xoá AI Model")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi cơ sở dữ liệu khi xoá. Cần kiểm tra xem model có đang được gán với RagConfig nào không.",
            )
