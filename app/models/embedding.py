# app/models/embedding.py

from sqlalchemy import String, Column, Text, Integer, ForeignKey, JSON, func, DateTime
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.rag_database import RagBase
import uuid

class Embedding(RagBase):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    content = Column(Text, nullable=False)

    embedding = Column(Vector(384), nullable=True) 

    metadata_ = Column("metadata", JSON, nullable=False)

    # Các trường phục vụ Hierarchical
    parent_node_id = Column(String, index=True, nullable=True)
    node_id = Column(String, index=True, unique=True)          
    level = Column(Integer, default=0)                        
    chunk_size = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())