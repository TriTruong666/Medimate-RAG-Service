from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from app.core.db.rag_database import get_db
from app.services import DocumentService
from app.core.common.interceptor import APIResponse

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