"""Per-run context and the live event channel.

Each chat turn runs inside a RunContext stored in a ContextVar. asyncio copies
context into the tasks LangGraph creates, so every node and tool sees the same
object without mutating shared tool instances.

Events go to LangGraph's custom stream (stream_mode="custom"), which the chat
service forwards to the client as SSE.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from langgraph.config import get_stream_writer

if TYPE_CHECKING:
    from app.browser.manager import BrowserSession

logger = structlog.get_logger()


@dataclass
class RunContext:
    run_id: str
    user_id: str
    session_id: str
    browser: BrowserSession | None = None
    tool_calls: int = 0
    browser_actions: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


_current_run: ContextVar[RunContext | None] = ContextVar("current_run", default=None)


def set_current_run(ctx: RunContext):
    return _current_run.set(ctx)


def reset_current_run(token) -> None:
    _current_run.reset(token)


def current_run() -> RunContext:
    ctx = _current_run.get()
    if ctx is None:
        raise RuntimeError("No active run context")
    return ctx


def emit(event: str, data: dict[str, Any]) -> None:
    """Send a live event to the client. No-op when running outside a streamed graph."""
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return
    writer({"event": event, "data": data})
