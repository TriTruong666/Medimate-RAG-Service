from fastapi import APIRouter, Depends
from app.core.common.interceptor import APIResponse
from app.core.db.rag_database import get_db
from app.services.rag_config_service import RagConfigService

router = APIRouter()

@router.get("/", summary="Lấy cấu hình RAG hiện tại", tags=["RAG Config"])
async def get_rag_config(
    db=Depends(get_db)
):
    config = RagConfigService.get_rag_config(db)

    return APIResponse.success(
        message="Lấy cấu hình RAG thành công",
        data=config
    )