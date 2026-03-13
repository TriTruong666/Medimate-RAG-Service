from fastapi import APIRouter, Depends, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from app.core.common.rate_limit import rate_limit_document_process
from app.core.db.rag_database import get_db
from app.services.document_service import DocumentService
from app.core.common.interceptor import APIResponse
from typing import Optional

router = APIRouter()
@router.post("/upload-document", status_code=status.HTTP_201_CREATED, summary="Upload tài liệu", tags=["Documents"])
async def upload_document(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    result = DocumentService.save_upload_file(db, file, file.filename)
    return APIResponse.success(
        data=result["data"],
        message=result["message"],
        status_code=status.HTTP_201_CREATED,
    )

@router.post("/{document_id}/process", status_code=status.HTTP_200_OK, summary="Xử lý tài liệu", tags=["Documents"])
async def process_document(
    document_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_document_process),
):
    result = DocumentService.process_document(db, document_id)
    return APIResponse.success(
        message=result["message"],
        data=None
    )

@router.get("/", status_code=status.HTTP_200_OK, summary="Lấy danh sách tài liệu", tags=["Documents"])
async def list_documents(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=100, description="Số lượng mỗi trang"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên tài liệu"),
    db: Session = Depends(get_db)
): 
    result = DocumentService.get_list_documents(db, page, limit, q)

    return APIResponse.success(
        message="Lấy danh sách thành công",
        data=result
    )

@router.get("/{document_id}", status_code=status.HTTP_200_OK, summary="Lấy thông tin tài liệu", tags=["Documents"])
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    result = DocumentService.get_document_by_id(db, document_id)
    return APIResponse.success(
        message="Lấy thông tin tài liệu thành công",
        data=result
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK, summary="Xoá tài liệu (bao gồm dữ liệu đã embedded)", tags=["Documents"])
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    result = DocumentService.delete_document(db, document_id)
    return APIResponse.success(
        message=result["message"],
        data=None
    )