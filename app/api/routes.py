from fastapi import APIRouter
from app.api.endpoints import documents, chat, rag_config

router = APIRouter()

router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(rag_config.router, prefix="/rag-config", tags=["RAG Config"])