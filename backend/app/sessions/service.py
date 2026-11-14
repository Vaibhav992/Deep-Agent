from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatMessage
from app.sessions.models import Session
from app.sessions.schemas import SessionCreate, SessionUpdate
from app.utils.id_generator import generate_id


async def create_session(
    db: AsyncSession, user_id: str, data: SessionCreate
) -> Session:
    session = Session(
        id=generate_id("sess"),
        user_id=user_id,
        title=data.title,
        model_preference=data.model_preference,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(
    db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0
) -> list[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_session(
    db: AsyncSession, session_id: str, user_id: str
) -> Session | None:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id, Session.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_messages(db: AsyncSession, session_id: str, limit: int = 200) -> list[ChatMessage]:
    """Most recent `limit` messages of a session, oldest first."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def update_session(
    db: AsyncSession, session_id: str, user_id: str, data: SessionUpdate
) -> Session | None:
    session = await get_session(db, session_id, user_id)
    if not session:
        return None

    if data.title is not None:
        session.title = data.title
    if data.model_preference is not None:
        session.model_preference = data.model_preference

    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(
    db: AsyncSession, session_id: str, user_id: str
) -> bool:
    session = await get_session(db, session_id, user_id)
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True
