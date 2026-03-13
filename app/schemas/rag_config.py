from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RagConfigBase(BaseModel):
    embedding_model: str = Field(..., min_length=1)
    llm_model: str = Field(..., min_length=1)
    chunk_size: int = Field(512, ge = 64, le = 4096)
    top_k: int = Field(5, ge = 1, le = 20)
    temperature: float = Field(0.1, ge = 0.0, le = 2.0)
    max_tokens: int = Field(512, ge = 32, le = 4096)
    context_window: int = Field(3900, ge = 256, le = 32768)
    prompt_template: str = Field(..., min_length=1)
    response_type: str = Field("standard")
    is_use_api: bool = True

class RagConfigCreate(RagConfigBase):
    pass

class RagConfigUpdate(BaseModel):
    embedding_model: Optional[str] = None
    llm_model: Optional[str] = None
    chunk_size: Optional[int] = Field(None, ge=64, le=4096)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1024)
    top_k: Optional[int] = Field(None, ge=1, le=20)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=32, le=4096)
    context_window: Optional[int] = Field(None, ge=256, le=32768)
    prompt_template: Optional[str] = None
    response_type: Optional[str] = None
    is_use_api: Optional[bool] = None

class RagConfigResponse(RagConfigBase):
    id: int
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)