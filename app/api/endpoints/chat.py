from fastapi import APIRouter
from fastapi.responses import StreamingResponse 
from app.services.chat_service import ChatService
from app.services.rag_engine import initialize_global_engine 
from app.schemas.chat import ChatRequest
router = APIRouter()


_stream_engine_cache = None
_completion_engine_cache = None

def get_cached_engine(streaming: bool):
    global _stream_engine_cache, _completion_engine_cache
    
    if streaming:
        if _stream_engine_cache is None:
            _stream_engine_cache = initialize_global_engine(streaming=True)
        return _stream_engine_cache
    else:
        if _completion_engine_cache is None:
            _completion_engine_cache = initialize_global_engine(streaming=False)
        return _completion_engine_cache


@router.post("/stream", summary="Chat với Model LLM (Streaming)", tags=["Chat"])
async def chat_stream(req: ChatRequest):
    engine = get_cached_engine(streaming=True)

    data_generator = ChatService.chat_stream_generator(engine, req.question)
    
    return StreamingResponse(
        data_generator, 
        media_type="application/x-ndjson" 
    )

@router.post("/completion", summary="Chat với Model LLM (Non-Streaming)", tags=["Chat"])
async def chat_completion(req: ChatRequest):
    engine = get_cached_engine(streaming=False)
    
    data_generator = ChatService.chat_completion_generator(engine, req.question)
    
    return StreamingResponse(
        data_generator, 
        media_type="application/x-ndjson" 
    )