from sqlalchemy import Column, String, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.rag_database import RagBase
import uuid

class ChatLog(RagBase):
    __tablename__ = "chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    user_message = Column(String, nullable=False)
    assistant_response = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())