import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatMessage
from app.chat.schemas import ChatRequest
from app.sessions import service as session_service
from app.utils.id_generator import generate_id


async def process_chat_echo(
    db: AsyncSession, user_id: str, request: ChatRequest
) -> ChatMessage:
    """Echo-mode chat: stores the message and echoes it back.

    This is the Phase 1 placeholder. Phase 2 replaces this with
    the LangGraph agent invocation.
    """
    start = time.monotonic()

    # Save user message
    user_msg = ChatMessage(
        id=generate_id("msg"),
        session_id=request.session_id,
        user_id=user_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)

    # Generate echo response
    echo_content = f"[Echo] {request.message}"
    model_used = request.model or "echo"
    provider = request.provider or "local"

    elapsed_ms = (time.monotonic() - start) * 1000

    assistant_msg = ChatMessage(
        id=generate_id("msg"),
        session_id=request.session_id,
        user_id=user_id,
        role="assistant",
        content=echo_content,
        model_used=model_used,
        provider=provider,
        latency_ms=elapsed_ms,
    )
    db.add(assistant_msg)

    # Update session stats
    session = await session_service.get_session(db, request.session_id, user_id)
    if session:
        session.message_count += 2

    await db.commit()
    await db.refresh(assistant_msg)
    return assistant_msg
