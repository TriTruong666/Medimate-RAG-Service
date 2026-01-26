from fastapi import APIRouter, Depends
# 1. QUAN TRỌNG: Import cái này từ FastAPI
from fastapi.responses import StreamingResponse 
from app.services.chat_service import ChatService
from app.services.rag_engine import initialize_global_engine

router = APIRouter()

# Biến global lưu engine (để đỡ load lại)
_global_engine = None

def get_engine():
    global _global_engine
    if _global_engine is None:
        _global_engine = initialize_global_engine()
    return _global_engine

@router.post("/stream", summary="Chat với RAG Engine (Streaming)", tags=["Chat"])
async def chat_stream(question: str):
    # 1. Lấy Engine
    engine = get_engine()
    
    # 2. Tạo Generator (Cái hàm ông vừa viết)
    # Hàm này trả về 1 cái "vòi nước" (iterator), chưa chạy ngay
    data_generator = ChatService.chat_stream_generator(engine, question)
    
    # 3. Trả về StreamingResponse
    # FastAPI sẽ kích hoạt cái vòi nước kia, lấy từng giọt (yield) và bắn về client
    return StreamingResponse(
        data_generator, 
        media_type="application/x-ndjson" # Định dạng chuẩn cho JSON Streaming
    )