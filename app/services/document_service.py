import os
import hashlib
import shutil
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from sqlalchemy.orm import Session
from app.schemas import Document


class DocumentService:
    @staticmethod
    def save_upload_file(db: Session, file: UploadFile, filename: str):
        file_checksum = calculate_file_hash(file)

        existed_doc = (
            db.query(Document).filter(Document.checksum == file_checksum).first()
        )

        if existed_doc:
            raise HTTPException(status_code=400, message="File này đã tồn tại rồi")

        file_path = os.path.join(settings.RAW_UPLOAD_PATH, filename)
        if os.path.exists(file_path):
            filename = f"{file_checksum[:8]}_{filename}"
            file_path = os.path.join(settings.RAW_DOCS_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        new_doc = Document(
            doc_name=filename,
            file_path=file_path,
            type=filename.split(".")[-1],
            status="uploaded",
            checksum=file_checksum,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        return {"message": f"Upload file {filename} thành công", "data": new_doc}


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
