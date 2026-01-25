from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class DocumentResponse(BaseModel):
    id: UUID
    doc_name: str
    file_path: str
    type: str
    status: str
    file_size: int
    checksum: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class PaginationSchema(BaseModel):
    current_page: int
    total_pages: int
    limit: int
    total_records: int

class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    pagination: PaginationSchema