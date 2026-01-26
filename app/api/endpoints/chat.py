from fastapi import APIRouter, Depends
# 1. QUAN TRỌNG: Import cái này từ FastAPI
from fastapi.responses import StreamingResponse 
from app.services.chat_service import ChatService
from app.services.rag_engine import initialize_global_engine

router = APIRouter()

_global_engine = None

def get_engine(streaming: bool = True):
    global _global_engine
    if _global_engine is None:
        _global_engine = initialize_global_engine(streaming)
    return _global_engine

@router.post("/stream", summary="Chat với Model LLM (Streaming)", tags=["Chat"])
async def chat_stream(question: str):
    engine = get_engine(True)
    
    data_generator = ChatService.chat_stream_generator(engine, question)
    
    return StreamingResponse(
        data_generator, 
        media_type="application/x-ndjson" 
    )

@router.post("/completion", summary="Chat với Model LLM (Non-Streaming)", tags=["Chat"])
async def chat_completion(question: str):
    engine = get_engine(False)
    
    data_generator = ChatService.chat_completion_generator(engine, question)
    
    return StreamingResponse(
        data_generator, 
        media_type="application/x-ndjson" 
    )