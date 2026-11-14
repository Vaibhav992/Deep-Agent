"""Chat turn execution.

`run_turn` executes one agent run and yields typed events. The SSE endpoint
streams them; the blocking endpoint drains them. Event names (data fields):

  run_started  {run_id, session_id, user_message_id}
  node         {node, status: started|completed|failed, duration_ms?}
  plan         {steps:[{index,title,status}]}
  plan_step    {index, status: running|done|failed}
  tool_start   {call_id, tool, node, args}
  tool_end     {call_id, tool, ok, duration_ms, result}
  browser_session {status: open|closed, provider?, live_url?}
  browser_action  {call_id, action, target, value, url, title, ok, error, ts}
  browser_frame   {call_id, url, title, mime, data, width, height, ts}
  notice       {message}
  content      {content}
  blocked      {reason}
  error        {message}
  done         {message_id, status: completed|failed|cancelled|blocked, latency_ms, model, tool_calls, browser_actions}
"""
import asyncio
import time
from typing import AsyncGenerator

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import agent_graph
from app.agent.run_context import RunContext, reset_current_run, set_current_run
from app.chat.models import ChatMessage
from app.chat.schemas import ChatRequest
from app.db.database import async_session
from app.llm.providers import resolve_model
from app.memory.long_term_memory import get_ltm_for_context
from app.memory.working_memory import append_to_working_memory
from app.observability.langfuse_setup import flush_langfuse, langfuse_run_config
from app.security.pipeline import GuardrailDecision
from app.security.pipeline import check_input as guardrail_check_input
from app.security.pipeline import check_output as guardrail_check_output
from app.sessions import service as session_service
from app.sessions.models import Session
from app.utils.id_generator import generate_id, generate_uuid

logger = structlog.get_logger()

_ANSWER_NODES = ("synthesizer", "direct_answer", "browser_agent")
# Persisted with the answer so history can replay the run. Frames are too large to keep.
_PERSISTED_EVENTS = {"node", "plan", "plan_step", "tool_start", "tool_end", "browser_action", "notice"}
_TITLE_CHARS = 60
_GRAPH_DONE = object()


async def _build_memory_context(db: AsyncSession, user_id: str) -> str:
    """Long-term facts about the user. In-session context comes from `_recent_history` as real messages."""
    try:
        ltm = await get_ltm_for_context(db, user_id)
    except Exception as e:
        logger.warning("memory_load_failed", error=str(e))
        return ""
    if not ltm:
        return ""
    return "<long_term_memory>\n" + "\n".join(f"- [{e['category']}] {e['content']}" for e in ltm) + "\n</long_term_memory>"


async def _recent_history(db: AsyncSession, session_id: str, limit: int = 8) -> list:
    """Last few turns of this session, so follow-up questions have context."""
    rows = await session_service.list_messages(db, session_id, limit=limit)
    history = []
    for m in rows:
        if m.role == "user":
            history.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            history.append(AIMessage(content=m.content))
    return history


def _title_from(message: str) -> str:
    text = " ".join(message.split())
    return text if len(text) <= _TITLE_CHARS else text[: _TITLE_CHARS - 1].rstrip() + "…"


async def run_turn(db: AsyncSession, user_id: str, request: ChatRequest, session: Session) -> AsyncGenerator[dict, None]:
    start = time.monotonic()
    run_id = generate_uuid()
    model_info = resolve_model(request.model, "fast")
    history = await _recent_history(db, request.session_id)

    user_msg = ChatMessage(
        id=generate_id("msg"), session_id=request.session_id, user_id=user_id,
        role="user", content=request.message,
    )
    db.add(user_msg)
    session.message_count += 1
    if session.message_count == 1 and session.title in ("", "New Chat", "New task"):
        session.title = _title_from(request.message)
    await db.commit()
    try:
        await append_to_working_memory(db, user_id, request.session_id, "user", request.message)
    except Exception as e:
        logger.warning("stm_append_failed", error=str(e))

    yield {"event": "run_started", "data": {
        "run_id": run_id, "session_id": request.session_id, "user_message_id": user_msg.id,
        "title": session.title,
    }}

    activity: list[dict] = []
    final_content = ""
    status = "completed"
    last_frame: dict | None = None
    ctx = RunContext(run_id=run_id, user_id=user_id, session_id=request.session_id)

    guard = await guardrail_check_input(request.message, user_id, request.session_id)
    if guard.decision == GuardrailDecision.BLOCKED:
        status = "blocked"
        final_content = f"I can't help with that request. {guard.reason or ''}".strip()
        yield {"event": "blocked", "data": {"reason": guard.reason}}
    else:
        memory_context = await _build_memory_context(db, user_id)
        messages = [SystemMessage(content=f"Memory context:\n{memory_context}")] if memory_context else []
        messages += [*history, HumanMessage(content=request.message)]

        initial_state = {
            "messages": messages, "user_id": user_id, "session_id": request.session_id,
            "mode": request.mode, "next_node": "", "from_node": "",
            "research_plan": [], "current_step": 0, "max_steps": 0,
            "gathered_context": [], "sources": [],
            "model_name": request.model, "purpose": "fast",
            "trace_id": run_id, "turn_start_time": start,
            "total_tokens_input": 0, "total_tokens_output": 0, "total_cost_usd": 0.0,
        }
        run_config = langfuse_run_config(
            user_id=user_id, session_id=request.session_id, trace_name="chat_turn",
            metadata={"model": request.model, "run_id": run_id, "mode": request.mode},
        )

        token = set_current_run(ctx)
        # The graph runs in its own task so a client disconnect can cancel it outright.
        # Cancelling only this generator would leave the running node (and its browser) alive.
        queue: asyncio.Queue = asyncio.Queue()

        async def drive_graph():
            try:
                async for item in agent_graph.astream(
                    initial_state, config=run_config, stream_mode=["custom", "updates"]
                ):
                    await queue.put(item)
                await queue.put(_GRAPH_DONE)
            except asyncio.CancelledError:
                raise
            except BaseException as e:
                await queue.put(e)

        graph_task = asyncio.create_task(drive_graph())
        handed_off = False
        try:
            while True:
                item = await queue.get()
                if item is _GRAPH_DONE:
                    break
                if isinstance(item, BaseException):
                    raise item
                mode, chunk = item
                if mode == "custom":
                    event = chunk
                    if event["event"] in _PERSISTED_EVENTS:
                        activity.append(event)
                    elif event["event"] == "browser_frame":
                        last_frame = event["data"]
                    yield event
                    continue
                for node_name, node_output in chunk.items():
                    if node_name in _ANSWER_NODES and isinstance(node_output, dict):
                        ai = [m for m in node_output.get("messages", []) if isinstance(m, AIMessage)]
                        if ai:
                            final_content = ai[-1].content

            if final_content:
                out_guard = await guardrail_check_output(final_content, user_id, request.session_id)
                if out_guard.decision == GuardrailDecision.BLOCKED:
                    final_content = "I produced an answer, but it was withheld by the safety filter. Try rephrasing the request."
                yield {"event": "content", "data": {"content": final_content}}
            else:
                status = "failed"
                final_content = "The agent finished without producing an answer."
                yield {"event": "error", "data": {"message": final_content}}
        except asyncio.CancelledError:
            # The client disconnected. sse-starlette cancels via an anyio scope that re-cancels every
            # later await here, so stopping the graph and saving the partial run happen in a detached task.
            logger.info("run_cancelled", run_id=run_id)
            msg = _assistant_message(request, user_id, final_content or "Stopped before finishing.",
                                     model_info, start, run_id, "cancelled", activity, last_frame, ctx)
            _spawn_detached(_finish_cancelled(graph_task, ctx, msg, session.id, user_id))
            handed_off = True
            raise
        except Exception as e:
            status = "failed"
            logger.error("run_failed", run_id=run_id, error=str(e), exc_info=e)
            final_content = "Something went wrong while running this task."
            yield {"event": "error", "data": {"message": f"{final_content} ({type(e).__name__})"}}
        finally:
            reset_current_run(token)
            if not handed_off:
                await _stop_graph(graph_task, ctx)
            flush_langfuse()

    assistant_msg = _assistant_message(request, user_id, final_content, model_info, start, run_id,
                                       status, activity, last_frame, ctx)
    # Detached with its own DB session: a disconnect arriving mid-commit must not abort the save
    # or close a session that is still committing.
    await asyncio.shield(_spawn_detached(_persist_assistant(assistant_msg, session.id, user_id)))

    yield {"event": "done", "data": {
        "message_id": assistant_msg.id, "status": status, "latency_ms": assistant_msg.latency_ms,
        "model": model_info.model_id, "tool_calls": ctx.tool_calls, "browser_actions": ctx.browser_actions,
    }}


def _assistant_message(request: ChatRequest, user_id: str, content: str, model_info, start: float, run_id: str,
                       status: str, activity: list[dict], last_frame: dict | None, ctx: RunContext) -> ChatMessage:
    return ChatMessage(
        id=generate_id("msg"), session_id=request.session_id, user_id=user_id,
        role="assistant", content=content,
        model_used=model_info.model_id, provider=model_info.provider,
        latency_ms=round((time.monotonic() - start) * 1000, 1),
        metadata_={
            "run_id": run_id, "status": status, "mode": request.mode,
            "activity": activity, "last_frame": last_frame,
            "tool_calls": ctx.tool_calls, "browser_actions": ctx.browser_actions,
        },
    )


async def _stop_graph(task: asyncio.Task, ctx: RunContext) -> None:
    """Cancel the graph task (if still running), wait for its cleanup, then make sure the browser is closed."""
    if not task.done():
        task.cancel()
    try:
        await task
    except BaseException:
        pass
    if ctx.browser is not None:
        await ctx.browser.close()


_background_tasks: set[asyncio.Task] = set()


def _spawn_detached(coro) -> asyncio.Task:
    task = asyncio.get_running_loop().create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _finish_cancelled(task: asyncio.Task, ctx: RunContext, msg: ChatMessage, session_id: str, user_id: str) -> None:
    await _stop_graph(task, ctx)
    await _persist_assistant(msg, session_id, user_id)


async def _persist_assistant(msg: ChatMessage, session_id: str, user_id: str) -> None:
    """Save the assistant message with a dedicated DB session (independent of the request's lifecycle)."""
    try:
        async with async_session() as db:
            db.add(msg)
            session = await session_service.get_session(db, session_id, user_id)
            if session is not None:
                session.message_count += 1
            await db.commit()
            try:
                await append_to_working_memory(db, user_id, session_id, "assistant", msg.content)
            except Exception as e:
                logger.warning("stm_append_failed", error=str(e))
    except Exception as e:
        logger.error("assistant_save_failed", error=str(e), session_id=session_id, run_status=msg.metadata_.get("status"))
