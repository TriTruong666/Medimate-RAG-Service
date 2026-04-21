from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    ai_model_id: str | None = Field(None, description="ID (UUID) của AIModel muốn sử dụng. Nếu không truyền sẽ lấy model mặc định.")
    client_id: str | None = Field(None, description="ID của client để quản lý task (SSE client_id)")