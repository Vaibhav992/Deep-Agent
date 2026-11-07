from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str | None = None
    provider: str | None = None


class ChatResponse(BaseModel):
    message_id: str
    content: str
    model_used: str
    provider: str
    tokens_input: int
    tokens_output: int
