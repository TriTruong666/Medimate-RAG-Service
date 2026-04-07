from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db.rag_database import get_db
from app.schemas.ai_model import AIModelCreate, AIModelResponse, AIModelUpdate
from app.services.ai_model_service import AIModelService

router = APIRouter()

@router.get(
    "/",
    response_model=List[AIModelResponse],
    summary="Lấy danh sách AI Model",
    description="Truy xuất toàn bộ danh sách AI Model đang có trong hệ thống, hỗ trợ phân trang."
)
def get_ai_models(
    skip: int = Query(0, description="Bỏ qua N kết quả đầu tiên"),
    limit: int = Query(100, description="Số lượng kết quả trả về tối đa"),
    db: Session = Depends(get_db),
):
    return AIModelService.get_list(db, skip=skip, limit=limit)


@router.get(
    "/{model_id}",
    response_model=AIModelResponse,
    summary="Lấy chi tiết AI Model",
    description="Tra cứu thông tin cấu hình chi tiết của một AI Model dựa trên UUID của nó."
)
def get_ai_model(
    model_id: UUID,
    db: Session = Depends(get_db),
):
    return AIModelService.get_by_id(db, model_id)


@router.post(
    "/",
    response_model=AIModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới AI Model",
    description="Thêm một model AI mới vào database, lưu cấu hình API hoặc config cục bộ dưới dạng JSON."
)
def create_ai_model(
    payload: AIModelCreate,
    db: Session = Depends(get_db),
):
    return AIModelService.create(db, payload)


@router.patch(
    "/{model_id}",
    response_model=AIModelResponse,
    summary="Cập nhật AI Model",
    description="Cập nhật một phần (Patch) cho AI Model cụ thể. Bạn có thể thay token API ở đây."
)
def update_ai_model(
    model_id: UUID,
    payload: AIModelUpdate,
    db: Session = Depends(get_db),
):
    return AIModelService.update(db, model_id, payload)


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá AI Model",
    description="Xoá một model khỏi database. Lưu ý sẽ gặp lỗi nếu model này đang được ưu tiên set trong bảng RAG config."
)
def delete_ai_model(
    model_id: UUID,
    db: Session = Depends(get_db),
):
    AIModelService.delete(db, model_id)
    return None
