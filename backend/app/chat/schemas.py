from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=8000)
    model: str | None = None
    provider: str | None = None
    mode: Literal["auto", "research", "browse", "quick"] = "auto"


class ChatResponse(BaseModel):
    message_id: str
    content: str
    status: str
    model_used: str
    latency_ms: float


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    model_used: str | None
    latency_ms: float
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
