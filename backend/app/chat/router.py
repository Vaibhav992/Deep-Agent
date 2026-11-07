import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import process_chat_echo
from app.sessions import service as session_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, data.session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg = await process_chat_echo(db, user.id, data)
    return ChatResponse(
        message_id=msg.id,
        content=msg.content,
        model_used=msg.model_used or "echo",
        provider=msg.provider or "local",
        tokens_input=msg.tokens_input,
        tokens_output=msg.tokens_output,
    )


@router.post("/stream")
async def chat_stream(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming endpoint. Phase 1: echoes via SSE events.
    Phase 2: streams LangGraph agent tokens.
    """
    session = await session_service.get_session(db, data.session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        yield {"event": "content", "data": json.dumps({"token": f"[Echo] {data.message}"})}
        yield {"event": "done", "data": json.dumps({"model": "echo", "provider": "local"})}

    return EventSourceResponse(event_generator())
