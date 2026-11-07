import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import process_chat, process_chat_stream
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

    msg = await process_chat(db, user.id, data)
    return ChatResponse(
        message_id=msg.id,
        content=msg.content,
        model_used=msg.model_used or "gemini-2.5-flash",
        provider=msg.provider or "gemini",
        tokens_input=msg.tokens_input,
        tokens_output=msg.tokens_output,
    )


@router.post("/stream")
async def chat_stream(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming endpoint. Streams agent graph node events + final answer."""
    session = await session_service.get_session(db, data.session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        async for event in process_chat_stream(db, user.id, data):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())
