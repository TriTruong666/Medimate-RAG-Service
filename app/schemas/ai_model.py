from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class AIModelBase(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        title="Tên Model", 
        description="Tên định danh duy nhất của model (Vd: gpt-4o, bge-m3, gemini-2.5-pro)",
        examples=["gpt-4o"]
    )
    provider: str = Field(
        ..., 
        min_length=1, 
        title="Nhà cung cấp", 
        description="Nhà cung cấp model (Vd: openai, google, ollama, huggingface)",
        examples=["openai"]
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, 
        title="Cấu hình Model", 
        description="Lưu trữ cấu hình động dạng JSON để dùng model (api_key, base_url, version...)",
        examples=[{"api_key": "YOUR_API_KEY", "model_name": "gpt-4o", "temperature": 0.2}]
    )
    context_window: int = Field(
        128000, 
        ge=1, 
        title="Context Window", 
        description="Số lượng token tối đa mà model có thể nhận (Đầu vào + Đầu ra)",
        examples=[128000]
    )
    max_output_tokens: int = Field(
        4096, 
        ge=1, 
        title="Token đầu ra tối đa", 
        description="Số token tối đa model có thể sinh ra trong 1 câu trả lời",
        examples=[4096]
    )
    is_active: bool = Field(
        True, 
        title="Trạng thái kích hoạt", 
        description="Xác định model có đang hoạt động hay không",
    )


class AIModelCreate(AIModelBase):
    pass


class AIModelUpdate(BaseModel):
    name: Optional[str] = Field(None, title="Tên Model", min_length=1)
    provider: Optional[str] = Field(None, title="Nhà cung cấp", min_length=1)
    config: Optional[Dict[str, Any]] = Field(None, title="Cấu hình Model")
    context_window: Optional[int] = Field(None, ge=1, title="Context Window")
    max_output_tokens: Optional[int] = Field(None, ge=1, title="Token đầu ra tối đa")
    is_active: Optional[bool] = Field(None, title="Trạng thái kích hoạt")


class AIModelResponse(AIModelBase):
    id: UUID = Field(..., title="ID", description="UUID duy nhất của record")
    created_at: datetime = Field(..., title="Thời gian tạo")
    updated_at: datetime = Field(..., title="Thời gian cập nhật gần nhất")

    model_config = ConfigDict(from_attributes=True)
