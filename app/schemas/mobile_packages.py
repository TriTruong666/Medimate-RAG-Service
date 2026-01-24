from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from app.core.db.rag_database import RagBase


class MobilePackage(RagBase):
    __tablename__ = "mobile_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # app so sánh version này, nếu length của table tăng thì tải, lấy dữ liệu mới nhất
    version = Column(String, unique=True, nullable=False)

    # (vd: data/exports/knowledge_v2.db)
    file_path = Column(String, nullable=False)
    file_hash = Column(String)

    description = Column(String)  # ghi chú cập nhật

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)  # Chỉ cho tải bản active
