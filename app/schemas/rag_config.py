from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class RagConfigBase(BaseModel):
    name: str = Field(..., min_length=1)
    default_llm_id: Optional[UUID] = None
    top_k: int = Field(10, ge=1, le=50)
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    prompt_template: str = Field(..., min_length=1)
    temperature: float = Field(0.2, ge=0.0, le=1.0)


class RagConfigCreate(RagConfigBase):
    pass


class RagConfigUpdate(BaseModel):
    name: Optional[str] = None
    default_llm_id: Optional[UUID] = None
    top_k: Optional[int] = Field(None, ge=1, le=50)
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    prompt_template: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)


class RagConfigResponse(RagConfigBase):
    id: int
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)