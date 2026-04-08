from fastapi import APIRouter, Depends
from app.core.auth.deps import RequireAdmin
from app.core.common.interceptor import APIResponse
from app.core.db.rag_database import get_db
from app.schemas.rag_config import RagConfigCreate, RagConfigUpdate
from app.services.rag_config_service import RagConfigService

router = APIRouter()


@router.get("/current", summary="Lấy cấu hình RAG hiện tại", tags=["RAG Config"])
async def get_rag_config(
    db=Depends(get_db),
    # _principal=RequireAdmin,
):
    config = RagConfigService.get_rag_config(db)

    return APIResponse.success(message="Lấy cấu hình RAG thành công", data=config)


@router.get("/", summary="Lấy danh sách cấu hình", tags=["RAG Config"])
async def get_all_configs(
    db=Depends(get_db),
    # _principal=RequireAdmin,
):
    config = RagConfigService.list_configs(db)
    return APIResponse.success(message="Lấy danh sách cấu hình thành công", data=config)


@router.get("/{config_id}", summary="Lấy cấu hình RAG theo ID", tags=["RAG Config"])
async def get_config_by_id(
    config_id: int,
    db=Depends(get_db),
    # _principal=RequireAdmin,
):
    config = RagConfigService.get_config_by_id(db, config_id)
    return APIResponse.success(message="Lấy cấu hình RAG thành công", data=config)


@router.post("/", summary="Tạo cấu hình RAG mới", tags=["RAG Config"])
async def create_rag_config(
    payload: RagConfigCreate,
    db=Depends(get_db),
    # _principal=RequireAdmin,
):
    config = RagConfigService.create_config(db, payload)
    return APIResponse.success(message="Tạo cấu hình RAG thành công", data=config)


@router.put("/{config_id}", summary="Cập nhật cấu hình RAG", tags=["RAG Config"])
async def update_rag_config(
    config_id: int,
    payload: RagConfigUpdate,
    db=Depends(get_db),
    # _principal=RequireAdmin,
):
    config = RagConfigService.update_config(db, config_id, payload)
    return APIResponse.success(message="Cập nhật cấu hình RAG thành công", data=config)


@router.delete("/{config_id}", summary="Xoá cấu hình RAG", tags=["RAG Config"])
async def delete_rag_config(
    config_id: int,
    db=Depends(get_db),
    # _principal=RequireAdmin,
):
    result = RagConfigService.delete_config(db, config_id)
    return APIResponse.success(message="Xoá cấu hình RAG thành công", data=None)
