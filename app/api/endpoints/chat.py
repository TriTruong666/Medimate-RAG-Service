import time

from fastapi import APIRouter, Depends
from app.core.auth.deps import RequireAdminOrUser
from app.core.common.interceptor import APIResponse
from app.core.common.rate_limit import rate_limit_chat_completion
from app.services.chat_service import ChatService
from app.services.rag_engine import initialize_global_engine
from app.schemas.chat import ChatRequest

router = APIRouter()


_completion_engine_cache = {}


def get_cached_engine(ai_model_id: str = None):
    global _completion_engine_cache
    cache_key = ai_model_id if ai_model_id is not None else "default"

    if cache_key not in _completion_engine_cache:
        _completion_engine_cache[cache_key] = initialize_global_engine(
            streaming=False, ai_model_id=ai_model_id
        )
    return _completion_engine_cache[cache_key]


@router.post("/preload", summary="Preload Chat Engine", tags=["Chat"], dependencies=[RequireAdminOrUser])
async def preload_chat_engine():
    global _completion_engine_cache
    was_ready = "default" in _completion_engine_cache
    started_at = time.perf_counter()

    engine = get_cached_engine()
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    return APIResponse.success(
        message="Preload engine thành công",
        data={
            "was_ready": was_ready,
            "is_ready": engine is not None,
            "elapsed_ms": elapsed_ms,
        },
    )


# @router.post("/stream", summary="Chat với Model LLM (Streaming)", tags=["Chat"])
# async def chat_stream(req: ChatRequest):
#     engine = get_cached_engine(ai_model_id=req.ai_model_id, streaming=True)

#     data_generator = ChatService.chat_stream_generator(engine, req.question)

#     return StreamingResponse(
#         data_generator,
#         media_type="application/x-ndjson"
#     )


@router.post("/completion", summary="Chat với Model LLM (Non-Streaming)", tags=["Chat"], dependencies=[RequireAdminOrUser])
async def chat_completion(
    req: ChatRequest,
    _: None = Depends(rate_limit_chat_completion),
):
    quick_reply = ChatService.build_quick_reply(req.question)
    if quick_reply is not None:
        return APIResponse.success(data=quick_reply)

    engine = get_cached_engine(ai_model_id=req.ai_model_id)

    # Sử dụng phiên bản async để có thể cancel
    result = await ChatService.chat_completion_async(
        engine, req.question, client_id=req.client_id
    )

    return APIResponse.success(data=result)


@router.post("/stop", summary="Dừng quá trình chat", tags=["Chat"], dependencies=[RequireAdminOrUser])
async def stop_chat(client_id: str):
    """
    Dừng một task chat đang chạy cho client_id cụ thể.
    """
    success = await ChatService.stop_chat(client_id)
    if success:
        return APIResponse.success(message=f"Đã dừng task cho client {client_id}")
    return APIResponse.error(message=f"Không tìm thấy task đang chạy cho client {client_id}")
