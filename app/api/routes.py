from fastapi import APIRouter
from app.api.endpoints import documents, chat

router = APIRouter()

router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])