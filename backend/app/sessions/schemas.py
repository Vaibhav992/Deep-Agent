from pydantic import BaseModel
from datetime import datetime


class SessionCreate(BaseModel):
    title: str = "New Chat"
    model_preference: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    model_preference: str | None = None


class SessionResponse(BaseModel):
    id: str
    title: str
    model_preference: str | None
    message_count: int
    total_tokens: int
    total_cost_usd: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
