import uuid
from sqlalchemy import Column, String, DateTime, func, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.db.rag_database import RagBase


class AIModel(RagBase):
    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tên định danh (vd: gpt-4o, gemini-1.5-pro)
    name = Column(String, nullable=False, unique=True)
    provider = Column(String, nullable=False) # openai, google, anthropic...
    
    # Cấu hình API (api_key, api_base, version...)
    config = Column(JSONB, nullable=True) 

    # Thông số kỹ thuật để code tự tính toán logic RAG
    context_window = Column(Integer, default=128000) 
    max_output_tokens = Column(Integer, default=4096)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())