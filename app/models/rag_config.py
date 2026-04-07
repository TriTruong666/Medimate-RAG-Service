from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.rag_database import RagBase


class RagConfig(RagBase):
    __tablename__ = "rag_configs"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True) # Ví dụ: "Chế độ chuyên gia", "Chế độ trả lời nhanh"
    
    # default_llm_id cũng để ở đây để biết config này ưu tiên dùng model nào
    default_llm_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    default_llm = relationship("AIModel", foreign_keys=[default_llm_id])

    # Các thông số điều khiển việc lấy dữ liệu (Retrieval)
    top_k = Column(Integer, default=10) # Lấy bao nhiêu tinh hoa từ toàn bộ kho
    threshold = Column(Float, default=0.5) # Độ tương đồng tối thiểu để lấy dữ liệu
    
    prompt_template = Column(Text)
    temperature = Column(Float, default=0.2)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
