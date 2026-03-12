from sqlalchemy import Column, String, DateTime, func, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.rag_database import RagBase
import uuid

class Collection(RagBase):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True) # tên collection
    description = Column(Text)
    is_active = Column(Boolean, default=True) # Có thể dùng để tạm thời vô hiệu hóa collection mà không xóa dữ liệu
    created_at = Column(DateTime(timezone=True), server_default=func.now())