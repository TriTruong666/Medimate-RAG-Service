import os
import hashlib
import shutil
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models import Document
from app.core.common.interceptor import APIResponse
from app.schemas.document import DocumentResponse

class DocumentService:
    file_types = ["pdf", "docx", "txt", "text", "doc", "json"]
    @staticmethod
    def save_upload_file(db: Session, file: UploadFile, filename: str):
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in DocumentService.file_types:
            APIResponse.error(message="Loại file không hợp lệ, chỉ chấp nhận: " + ", ".join(allowed_types), status_code=400)
            return

        file_checksum = calculate_file_hash(file)

        existed_doc = (
            db.query(Document).filter(Document.checksum == file_checksum).first()
        )

        if existed_doc:
            APIResponse.error(message="File đã tồn tại trong hệ thống", status_code=400)
            return

        file_path = os.path.join(settings.RAW_UPLOAD_PATH, filename)
        if os.path.exists(file_path):
            filename = f"{file_checksum[:8]}_{filename}"
            file_path = os.path.join(settings.RAW_UPLOAD_PATH, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size_in_bytes = os.path.getsize(file_path)

        new_doc = Document(
            doc_name=filename.split(".")[0],
            file_path=file_path,
            type=filename.split(".")[-1],
            status="uploaded",
            checksum=file_checksum,
            file_size=file_size_in_bytes,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        doc_schema = DocumentResponse.model_validate(new_doc)

        return {"message": f"Upload file {filename} thành công", "data": doc_schema}


def calculate_file_hash(file: UploadFile) -> str:
    """
    Đọc file và tính ra chuỗi SHA256 (Vân tay duy nhất)
    """
    sha256_hash = hashlib.sha256()

    # Đưa con trỏ về đầu file để đọc từ đầu
    file.file.seek(0)

    # Đọc từng miếng 4KB để không ngốn RAM nếu file to
    for byte_block in iter(lambda: file.file.read(4096), b""):
        sha256_hash.update(byte_block)

    # QUAN TRỌNG: Đọc xong con trỏ đang ở cuối file.
    # Phải đưa về đầu file (seek 0) để lát nữa hàm save còn đọc được mà lưu.
    file.file.seek(0)

    return sha256_hash.hexdigest()

        