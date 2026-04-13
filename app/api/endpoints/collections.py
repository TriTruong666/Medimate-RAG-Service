from fastapi import APIRouter, Depends, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.db.rag_database import get_db
from app.core.auth.deps import RequireAdmin, RequireAdminOrUser
from app.services.collection_service import CollectionService
from app.services.document_service import DocumentService
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionDocumentsUpdate,
    CollectionDetailResponse,
)
from app.core.common.interceptor import APIResponse
from typing import Optional
from uuid import UUID

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới collection",
    tags=["Collections"],
    dependencies=[RequireAdmin],
)
async def create_collection(
    collection_in: CollectionCreate, db: Session = Depends(get_db)
):
    result = CollectionService.create_collection(db, collection_in)
    return APIResponse.success(
        data=result,
        message="Tạo collection thành công",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách collection",
    tags=["Collections"],
    dependencies=[RequireAdminOrUser],
)
async def list_collections(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=100, description="Số lượng mỗi trang"),
    q: Optional[str] = Query(None, description="Tìm kiếm theo tên collection"),
    db: Session = Depends(get_db),
):
    result = CollectionService.get_list_collections(db, page, limit, q)
    return APIResponse.success(
        data=result, message="Lấy danh sách collection thành công"
    )


@router.get(
    "/{collection_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết collection",
    tags=["Collections"],
    dependencies=[RequireAdminOrUser],
)
async def get_collection(collection_id: UUID, db: Session = Depends(get_db)):
    result = CollectionService.get_collection_by_id(db, collection_id)
    # result already has 'documents' due to relationship and lazy='selectin'
    return APIResponse.success(
        data=CollectionDetailResponse.model_validate(result),
        message="Lấy thông tin collection thành công",
    )


@router.patch(
    "/{collection_id}",
    status_code=status.HTTP_200_OK,
    summary="Cập nhật collection",
    tags=["Collections"],
    dependencies=[RequireAdmin],
)
async def update_collection(
    collection_id: UUID, collection_in: CollectionUpdate, db: Session = Depends(get_db)
):
    result = CollectionService.update_collection(db, collection_id, collection_in)
    return APIResponse.success(data=result, message="Cập nhật collection thành công")


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa collection",
    tags=["Collections"],
    dependencies=[RequireAdmin],
)
async def delete_collection(collection_id: UUID, db: Session = Depends(get_db)):
    result = CollectionService.delete_collection(db, collection_id)
    return APIResponse.success(message=result["message"])


@router.post(
    "/{collection_id}/assign-documents",
    status_code=status.HTTP_200_OK,
    summary="Gán danh sách tài liệu vào collection (bổ sung)",
    tags=["Collections"],
    dependencies=[RequireAdmin],
)
async def assign_documents(
    collection_id: UUID,
    payload: CollectionDocumentsUpdate,
    db: Session = Depends(get_db),
):
    result = CollectionService.assign_documents(db, collection_id, payload.document_ids)
    return APIResponse.success(message=result["message"])


@router.put(
    "/{collection_id}/documents",
    status_code=status.HTTP_200_OK,
    summary="Cập nhật/Sửa danh sách tài liệu trong collection (thay thế)",
    tags=["Collections"],
    dependencies=[RequireAdmin],
)
async def sync_documents(
    collection_id: UUID,
    payload: CollectionDocumentsUpdate,
    db: Session = Depends(get_db),
):
    result = CollectionService.sync_documents(db, collection_id, payload.document_ids)
    return APIResponse.success(message=result["message"])


@router.post(
    "/{collection_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Nạp toàn bộ tài liệu trong collection (SSE)",
    tags=["Collections"],
    dependencies=[RequireAdmin],
)
async def process_collection(
    collection_id: UUID,
    background_tasks: BackgroundTasks,
    payload: Optional[CollectionDocumentsUpdate] = None,
    client_id: Optional[str] = Query(None, description="ID của SSE client để nhận log"),
    db: Session = Depends(get_db),
):
    # Nếu có truyền danh sách ID, chỉ xử lý những ID đó
    if payload and payload.document_ids:
        background_tasks.add_task(
            DocumentService.bulk_process_documents, 
            db, 
            [str(uid) for uid in payload.document_ids], 
            client_id
        )
    else:
        # Ngược lại nạp toàn bộ collection
        background_tasks.add_task(
            DocumentService.process_collection, db, str(collection_id), client_id
        )

    return APIResponse.success(
        message="Yêu cầu xử lý Bulk Ingest đã được tiếp nhận. Vui lòng theo dõi tiến độ qua SSE.",
        data={"client_id": client_id},
        status_code=status.HTTP_202_ACCEPTED,
    )
