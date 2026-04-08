from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from .document import DocumentResponse, PaginationSchema

class CollectionBase(BaseModel):
    name: str = Field(..., description="Tên của collection", examples=["Medical FAQ"])
    description: Optional[str] = Field(None, description="Mô tả cho collection", examples=["Chứa các tài liệu về hỏi đáp y tế"])
    is_active: bool = Field(True, description="Trạng thái hoạt động của collection")

class CollectionCreate(CollectionBase):
    pass

class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Tên mới của collection")
    description: Optional[str] = Field(None, description="Mô tả mới của collection")
    is_active: Optional[bool] = Field(None, description="Cập nhật trạng thái hoạt động")

class CollectionResponse(CollectionBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CollectionDetailResponse(CollectionResponse):
    documents: List[DocumentResponse] = []


class CollectionListResponse(BaseModel):
    items: List[CollectionResponse]
    pagination: PaginationSchema

class CollectionDocumentsUpdate(BaseModel):
    document_ids: List[UUID] = Field(..., description="Danh sách ID của các documents muốn gán vào collection")
