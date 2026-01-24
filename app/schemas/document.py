from sqlalchemy import Column, String, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.rag_database import RagBase
import uuid


class Document(RagBase):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # pdf, docx, txt, json
    status = Column(String, default="indexed")  # indexed, processing, failed, success
    file_size = Column(Integer, default=0)
    checksum = Column(String, nullable=False)  # Tranh duplicate
    created_at = Column(DateTime(timezone=True), server_default=func.now())
