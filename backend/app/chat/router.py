import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import run_turn
from app.db.database import async_session, get_db
from app.sessions import service as session_service

router = APIRouter(prefix="/chat", tags=["chat"])


async def _require_session(db: AsyncSession, session_id: str, user_id: str):
    session = await session_service.get_session(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=ChatResponse)
async def chat(data: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Blocking variant: runs the turn to completion and returns the answer."""
    session = await _require_session(db, data.session_id, user.id)
    content, done = "", {}
    async for event in run_turn(db, user.id, data, session):
        if event["event"] in ("content", "error", "blocked"):
            content = event["data"].get("content") or event["data"].get("message") or event["data"].get("reason") or ""
        elif event["event"] == "done":
            done = event["data"]
    return ChatResponse(
        message_id=done.get("message_id", ""), content=content, status=done.get("status", "failed"),
        model_used=done.get("model", ""), latency_ms=done.get("latency_ms", 0.0),
    )


@router.post("/stream")
async def chat_stream(data: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Streams the agent run as typed SSE events. Closing the connection cancels the run."""
    await _require_session(db, data.session_id, user.id)

    async def events():
        # The stream outlives the request handler, so it owns its DB session rather than borrowing the request's.
        async with async_session() as stream_db:
            session = await session_service.get_session(stream_db, data.session_id, user.id)
            async for event in run_turn(stream_db, user.id, data, session):
                yield {"event": event["event"], "data": json.dumps(event["data"], default=str)}

    return EventSourceResponse(events(), ping=15)
