from fastapi import APIRouter
from app.api.endpoints import documents, chat, rag_config, ai_model, collections, sse

router = APIRouter()

router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(rag_config.router, prefix="/rag-config", tags=["RAG Config"])
router.include_router(ai_model.router, prefix="/ai-models", tags=["AI Models"])
router.include_router(collections.router, prefix="/collections", tags=["Collections"])
router.include_router(sse.router, prefix="/sse", tags=["SSE"])
