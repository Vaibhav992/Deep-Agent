"""Long-term memory (LTM) — Tier 3 of the 3-tier memory system.

Persistent facts, preferences, rules, and skills written by the
agent via the write_memory tool. Loaded into agent context via
<long_term_memory> tags.
"""
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LongTermMemory

logger = structlog.get_logger()

VALID_CATEGORIES = {"fact", "preference", "rule", "skill"}


async def write_ltm(
    db: AsyncSession,
    user_id: str,
    category: str,
    content: str,
    importance: str = "medium",
    session_id: str | None = None,
) -> uuid.UUID:
    """Write a new long-term memory entry."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

    ltm = LongTermMemory(
        user_id=user_id,
        category=category,
        content=content,
        importance=importance,
        source_session_id=session_id,
        source_date=datetime.now(timezone.utc),
    )
    db.add(ltm)
    await db.commit()
    logger.info("ltm_written", user_id=str(user_id), category=category)
    return ltm.id


async def get_ltm_for_context(
    db: AsyncSession,
    user_id: str,
    categories: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    """Load LTM entries for injection into agent context."""
    query = select(LongTermMemory).where(LongTermMemory.user_id == user_id)
    if categories:
        query = query.where(LongTermMemory.category.in_(categories))
    query = query.order_by(LongTermMemory.created_at.desc()).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "category": e.category,
            "content": e.content,
            "importance": e.importance,
        }
        for e in entries
    ]
