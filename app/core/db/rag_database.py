from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..config import settings

rag_engine = create_engine(settings.RAG_DB_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=rag_engine, autocommit=False, autoflush=False)

RagBase = declarative_base()
