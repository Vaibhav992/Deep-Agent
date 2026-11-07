import time
import uuid as _uuid
from typing import AsyncGenerator

import structlog
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import agent_graph
from app.agent.state import AgentState
from app.chat.models import ChatMessage
from app.chat.schemas import ChatRequest
from app.events.producer import KafkaProducer
from app.events.schemas import NodeStartedEvent, NodeCompletedEvent
from app.memory.working_memory import load_working_memory, append_to_working_memory
from app.memory.long_term_memory import get_ltm_for_context
from app.sessions import service as session_service
from app.utils.id_generator import generate_id, generate_uuid

logger = structlog.get_logger()


async def _build_memory_context(db: AsyncSession, user_id: str, session_id: str) -> str:
    """Load STM + LTM and format as context for the agent."""
    parts = []
    try:
        uid = _uuid.UUID(user_id)
        sid = _uuid.UUID(session_id)

        stm = await load_working_memory(db, uid, sid)
        if stm:
            stm_text = "\n".join(f"[{e.get('role', '?')}] {e.get('content', '')}" for e in stm[-10:])
            parts.append(f"<working_memory>\n{stm_text}\n</working_memory>")

        ltm = await get_ltm_for_context(db, uid)
        if ltm:
            ltm_text = "\n".join(f"- [{e['category']}] {e['content']}" for e in ltm)
            parts.append(f"<long_term_memory>\n{ltm_text}\n</long_term_memory>")
    except Exception as e:
        logger.warning("memory_load_failed", error=str(e))

    return "\n\n".join(parts)


async def process_chat(
    db: AsyncSession, user_id: str, request: ChatRequest
) -> ChatMessage:
    """Run the agent graph and return the final assistant message."""
    start = time.monotonic()
    trace_id = generate_uuid()

    user_msg = ChatMessage(
        id=generate_id("msg"),
        session_id=request.session_id,
        user_id=user_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)

    # Load memory context (STM + LTM)
    memory_context = await _build_memory_context(db, user_id, request.session_id)
    messages = []
    if memory_context:
        messages.append(SystemMessage(content=f"Memory context:\n{memory_context}"))
    messages.append(HumanMessage(content=request.message))

    # Save user message to STM
    try:
        uid = _uuid.UUID(user_id)
        sid = _uuid.UUID(request.session_id)
        await append_to_working_memory(db, uid, sid, "user", request.message)
    except Exception as e:
        logger.warning("stm_append_failed", error=str(e))

    initial_state: AgentState = {
        "messages": messages,
        "user_id": user_id,
        "session_id": request.session_id,
        "next_node": "",
        "from_node": "",
        "research_plan": [],
        "current_step": 0,
        "max_steps": 0,
        "gathered_context": [],
        "sources": [],
        "model_name": request.model,
        "purpose": "fast",
        "trace_id": trace_id,
        "turn_start_time": start,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
    }

    result = await agent_graph.ainvoke(initial_state)

    final_messages = result.get("messages", [])
    ai_messages = [m for m in final_messages if isinstance(m, AIMessage)]
    final_content = ai_messages[-1].content if ai_messages else "No response generated."

    elapsed_ms = (time.monotonic() - start) * 1000
    model_used = request.model or "gemini-2.5-flash"
    provider = request.provider or "gemini"

    assistant_msg = ChatMessage(
        id=generate_id("msg"),
        session_id=request.session_id,
        user_id=user_id,
        role="assistant",
        content=final_content,
        model_used=model_used,
        provider=provider,
        latency_ms=elapsed_ms,
    )
    db.add(assistant_msg)

    session = await session_service.get_session(db, request.session_id, user_id)
    if session:
        session.message_count += 2

    # Save assistant response to STM
    try:
        await append_to_working_memory(db, uid, sid, "assistant", final_content)
    except Exception as e:
        logger.warning("stm_append_failed", error=str(e))

    await db.commit()
    await db.refresh(assistant_msg)

    logger.info(
        "chat_completed",
        session_id=request.session_id,
        trace_id=trace_id,
        latency_ms=round(elapsed_ms, 1),
        from_node=result.get("from_node", "unknown"),
    )

    return assistant_msg


async def process_chat_stream(
    db: AsyncSession, user_id: str, request: ChatRequest
) -> AsyncGenerator[dict, None]:
    """Stream agent graph execution as SSE events.

    Yields events as they happen:
    - {"event": "node", "data": {"node": "router", "status": "started"}}
    - {"event": "node", "data": {"node": "router", "status": "completed"}}
    - {"event": "step", "data": {"step": 1, "total": 3, "task": "..."}}
    - {"event": "content", "data": {"token": "..."}} (final answer)
    - {"event": "done", "data": {"model": "...", "latency_ms": ...}}
    """
    start = time.monotonic()
    trace_id = generate_uuid()

    user_msg = ChatMessage(
        id=generate_id("msg"),
        session_id=request.session_id,
        user_id=user_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)

    # Load memory context (STM + LTM)
    memory_context = await _build_memory_context(db, user_id, request.session_id)
    messages = []
    if memory_context:
        messages.append(SystemMessage(content=f"Memory context:\n{memory_context}"))
    messages.append(HumanMessage(content=request.message))

    # Save user message to STM
    try:
        uid = _uuid.UUID(user_id)
        sid = _uuid.UUID(request.session_id)
        await append_to_working_memory(db, uid, sid, "user", request.message)
    except Exception as e:
        logger.warning("stm_append_failed", error=str(e))

    initial_state: AgentState = {
        "messages": messages,
        "user_id": user_id,
        "session_id": request.session_id,
        "next_node": "",
        "from_node": "",
        "research_plan": [],
        "current_step": 0,
        "max_steps": 0,
        "gathered_context": [],
        "sources": [],
        "model_name": request.model,
        "purpose": "fast",
        "trace_id": trace_id,
        "turn_start_time": start,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
    }

    final_content = ""
    last_node = "unknown"
    model_used = request.model or "gemini-2.5-flash"
    provider = request.provider or "gemini"

    try:
        kafka = await KafkaProducer.get()
    except Exception:
        kafka = None

    async for event in agent_graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            last_node = node_name

            yield {"event": "node", "data": {"node": node_name, "status": "started"}}

            if kafka:
                await kafka.emit(
                    "agent.events",
                    NodeStartedEvent(session_id=request.session_id, node_name=node_name, trace_id=trace_id),
                    key=request.session_id,
                )

            if node_name == "planner" and "research_plan" in node_output:
                plan = node_output["research_plan"]
                for i, step in enumerate(plan):
                    yield {"event": "step", "data": {"step": i + 1, "total": len(plan), "task": step}}

            if node_name == "researcher" and "current_step" in node_output:
                step = node_output.get("current_step", 0)
                total = len(node_output.get("research_plan", initial_state.get("research_plan", [])))
                yield {"event": "progress", "data": {"step": step, "total": total}}

            new_messages = node_output.get("messages", [])
            ai_msgs = [m for m in new_messages if isinstance(m, AIMessage)]
            if ai_msgs:
                content = ai_msgs[-1].content
                if node_name in ("synthesizer", "direct_answer"):
                    final_content = content
                    yield {"event": "content", "data": {"token": content}}

            yield {"event": "node", "data": {"node": node_name, "status": "completed"}}

            if kafka:
                node_elapsed = (time.monotonic() - start) * 1000
                await kafka.emit(
                    "agent.events",
                    NodeCompletedEvent(
                        session_id=request.session_id,
                        node_name=node_name,
                        duration_ms=node_elapsed,
                        trace_id=trace_id,
                    ),
                    key=request.session_id,
                )

    elapsed_ms = (time.monotonic() - start) * 1000

    if not final_content:
        final_content = "No response generated."

    assistant_msg = ChatMessage(
        id=generate_id("msg"),
        session_id=request.session_id,
        user_id=user_id,
        role="assistant",
        content=final_content,
        model_used=model_used,
        provider=provider,
        latency_ms=elapsed_ms,
    )
    db.add(assistant_msg)

    session = await session_service.get_session(db, request.session_id, user_id)
    if session:
        session.message_count += 2

    # Save assistant response to STM
    try:
        await append_to_working_memory(db, uid, sid, "assistant", final_content)
    except Exception as e:
        logger.warning("stm_append_failed", error=str(e))

    await db.commit()

    yield {
        "event": "done",
        "data": {
            "message_id": assistant_msg.id,
            "model": model_used,
            "provider": provider,
            "latency_ms": round(elapsed_ms, 1),
        },
    }
