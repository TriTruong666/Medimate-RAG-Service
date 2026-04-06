from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

rag_engine = create_engine(settings.RAG_DB_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=rag_engine, autocommit=False, autoflush=False)


class RagBase(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()  # Mở kết nối
    try:
        yield db
    finally:
        db.close()


def setup_database():
    from sqlalchemy import text
    with rag_engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_embeddings_embedding_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_embeddings_fts_vector_gin ON embeddings USING GIN (fts_vector);"))
        conn.commit()
