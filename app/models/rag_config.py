from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func
from app.core.db.rag_database import RagBase


class RagConfig(RagBase):
    __tablename__ = "rag_configs"

    id = Column(Integer, primary_key=True)

    embedding_model = Column(String, nullable=False)
    llm_model = Column(String, nullable=False)

    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)

    top_k = Column(Integer, default=5)
    temperature = Column(Float, default=0.2)

    prompt_template = Column(Text)

    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
