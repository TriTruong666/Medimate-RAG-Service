from fastapi import APIRouter, Depends, UploadFile, File, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.auth.deps import RequireAdmin, RequireAdminOrUser
from app.core.common.rate_limit import rate_limit_document_process
from app.core.db.rag_database import get_db
from app.services.document_service import DocumentService
from app.schemas.document import DocumentResponse, BulkProcessRequest
from app.core.common.interceptor import APIResponse
from typing import Optional
from uuid import UUID

router = APIRouter()


@router.post(
    "/upload-document",
    status_code=status.HTTP_201_CREATED,
    summary="Upload tài liệu",
    tags=["Documents"],
)
async def upload_document(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    # _principal=RequireAdmin,
):
    result = DocumentService.save_upload_file(db, file, file.filename)
    return APIResponse.success(
        data=result["data"],
        message=result["message"],
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/bulk-upload-documents",
    status_code=status.HTTP_201_CREATED,
    summary="Upload nhiều tài liệu",
    tags=["Documents"],
)
async def bulk_upload_documents(
    db: Session = Depends(get_db),
    files: list[UploadFile] = File(...),
    # _principal=RequireAdmin,
):
    result = DocumentService.bulk_save_upload_files(db, files)
    return APIResponse.success(
        data=result,
        message=f"Đã xử lý {result['total']} files. Thành công: {result['success_count']}, Thất bại: {result['error_count']}",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/{document_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Xử lý tài liệu (SSE)",
    tags=["Documents"],
)
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    client_id: Optional[str] = Query(None, description="ID của SSE client để nhận log"),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_document_process),
    # _principal=RequireAdmin,
):
    # Đưa vào hàng đợi xử lý nền
    background_tasks.add_task(
        DocumentService.process_document, db, document_id, client_id
    )

    return APIResponse.success(
        message="Yêu cầu xử lý đã được tiếp nhận. Vui lòng theo dõi tiến độ qua SSE.",
        data={"client_id": client_id},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.post(
    "/bulk-process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Xử lý nhiều tài liệu cùng lúc (SSE)",
    tags=["Documents"],
)
async def bulk_process_documents(
    payload: BulkProcessRequest,
    background_tasks: BackgroundTasks,
    client_id: Optional[str] = Query(None, description="ID của SSE client để nhận log"),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_document_process),
    # _principal=RequireAdmin,
):
    # Đưa vào hàng đợi xử lý nền
    background_tasks.add_task(
        DocumentService.bulk_process_documents, db, [str(uid) for uid in payload.document_ids], client_id
    )

    return APIResponse.success(
        message="Yêu cầu xử lý Bulk Ingest đã được tiếp nhận. Vui lòng theo dõi tiến độ qua SSE.",
        data={"client_id": client_id},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/pending",
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách tài liệu đang chờ xử lý",
    tags=["Documents"],
)
async def pending_documents(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=100, description="Số lượng mỗi trang"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên tài liệu"),
    db: Session = Depends(get_db),
    # _principal=RequireAdminOrUser,
):
    result = DocumentService.get_pending_documents(db, page, limit, q)

    return APIResponse.success(message="Lấy danh sách thành công", data=result)


@router.get(
    "/uncollected",
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách tài liệu chưa có collection",
    tags=["Documents"],
)
async def uncollected_documents(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=100, description="Số lượng mỗi trang"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên tài liệu"),
    db: Session = Depends(get_db),
    # _principal=RequireAdminOrUser,
):
    result = DocumentService.get_uncollected_documents(db, page, limit, q)

    return APIResponse.success(message="Lấy danh sách thành công", data=result)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách tài liệu",
    tags=["Documents"],
)
async def list_documents(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=100, description="Số lượng mỗi trang"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên tài liệu"),
    db: Session = Depends(get_db),
    # _principal=RequireAdminOrUser,
):
    result = DocumentService.get_list_documents(db, page, limit, q)

    return APIResponse.success(message="Lấy danh sách thành công", data=result)


@router.get(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin tài liệu",
    tags=["Documents"],
)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    # _principal=RequireAdminOrUser,
):
    result = DocumentService.get_document_by_id(db, document_id)
    return APIResponse.success(message="Lấy thông tin tài liệu thành công", data=result)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Xoá tài liệu (bao gồm dữ liệu đã embedded)",
    tags=["Documents"],
)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    # _principal=RequireAdmin,
):
    result = DocumentService.delete_document(db, document_id)
    return APIResponse.success(message=result["message"], data=None)
