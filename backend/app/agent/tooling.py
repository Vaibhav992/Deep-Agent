"""Shared tool-call execution for agent nodes, with live tool events."""
import json
import time
import uuid
from contextvars import ContextVar

import structlog
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.agent.run_context import current_run, emit

logger = structlog.get_logger()

_PREVIEW_CHARS = 240

current_call_id: ContextVar[str | None] = ContextVar("current_call_id", default=None)


def preview(value, limit: int = _PREVIEW_CHARS) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def is_error_result(result: str) -> bool:
    return result.startswith(("[Error]", "[Blocked]"))


async def run_tool_calls(response: AIMessage, tools_by_name: dict[str, BaseTool], node: str) -> list[ToolMessage]:
    """Execute every tool call in `response`, emitting tool_start/tool_end for each."""
    ctx = current_run()
    messages: list[ToolMessage] = []
    for tc in response.tool_calls:
        call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:12]}"
        name = tc["name"]
        ctx.tool_calls += 1
        emit("tool_start", {"call_id": call_id, "tool": name, "node": node, "args": preview(tc.get("args", {}))})
        started = time.monotonic()

        token = current_call_id.set(call_id)
        try:
            tool_fn = tools_by_name.get(name)
            if tool_fn is None:
                result = f"[Error] Unknown tool: {name}"
            else:
                result = str(await tool_fn.ainvoke(tc.get("args", {})))
        except Exception as e:
            logger.error("tool_call_failed", tool=name, error=str(e), run_id=ctx.run_id)
            result = f"[Error] {name} failed: {e}"
        finally:
            current_call_id.reset(token)

        emit("tool_end", {
            "call_id": call_id,
            "tool": name,
            "ok": not is_error_result(result),
            "duration_ms": round((time.monotonic() - started) * 1000),
            "result": preview(result),
        })
        messages.append(ToolMessage(content=result, tool_call_id=call_id, name=name))
    return messages
