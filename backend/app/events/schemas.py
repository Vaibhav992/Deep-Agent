from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any
import uuid


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str | None = None


# --- agent.events ---

class NodeStartedEvent(BaseEvent):
    event_type: str = "node_started"
    session_id: str
    node_name: str
    input_preview: str | None = None


class NodeCompletedEvent(BaseEvent):
    event_type: str = "node_completed"
    session_id: str
    node_name: str
    duration_ms: float
    tokens_used: int = 0
    cost_usd: float = 0.0


class ToolCalledEvent(BaseEvent):
    event_type: str = "tool_called"
    session_id: str
    tool_name: str
    args_preview: dict[str, Any] = {}


class ToolResultEvent(BaseEvent):
    event_type: str = "tool_result"
    session_id: str
    tool_name: str
    success: bool
    duration_ms: float
    result_preview: str | None = None


# --- embedding.jobs ---

class EmbedDocumentEvent(BaseEvent):
    event_type: str = "embed_document"
    user_id: str
    doc_type: str
    source_id: str
    text_chunks: list[str]


# --- guardrail.events ---

class GuardrailCheckEvent(BaseEvent):
    event_type: str = "input_checked"
    user_id: str
    session_id: str
    direction: str
    layer: str
    decision: str
    confidence: float | None = None
    jev_response: dict | None = None
    latency_ms: float = 0.0


# --- browser.events ---

class BrowserActionEvent(BaseEvent):
    event_type: str = "element_clicked"
    session_id: str
    url: str | None = None
    action: str
    selector: str | None = None
    success: bool = True


# --- memory.events ---

class MemoryEvent(BaseEvent):
    event_type: str = "stm_updated"
    user_id: str
    session_id: str | None = None
    memory_type: str
    record_id: str | None = None


# --- session.events ---

class SessionLifecycleEvent(BaseEvent):
    event_type: str = "session_created"
    user_id: str
    session_id: str
