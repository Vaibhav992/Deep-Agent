"""Working memory (STM) — Tier 1 of the 3-tier memory system.

Per user + session + day. Loaded every turn into agent context.
Auto-compressed to archive when token count exceeds threshold.
"""
import uuid
from datetime import date, datetime, timezone

import structlog
import tiktoken
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WorkingMemory, WorkingMemoryArchive

logger = structlog.get_logger()

_TOKEN_THRESHOLD = 4000
_enc = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


async def load_working_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> list[dict]:
    """Load today's STM entries for context injection."""
    today = date.today()
    result = await db.execute(
        select(WorkingMemory).where(
            and_(
                WorkingMemory.user_id == user_id,
                WorkingMemory.session_id == session_id,
                WorkingMemory.date == today,
            )
        )
    )
    wm = result.scalar_one_or_none()
    if wm is None:
        return []
    return wm.entries or []


async def append_to_working_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    role: str,
    content: str,
) -> bool:
    """Add an entry to today's STM. Returns True if compression needed."""
    today = date.today()
    now = datetime.now(timezone.utc).isoformat()

    result = await db.execute(
        select(WorkingMemory).where(
            and_(
                WorkingMemory.user_id == user_id,
                WorkingMemory.session_id == session_id,
                WorkingMemory.date == today,
            )
        )
    )
    wm = result.scalar_one_or_none()

    entry = {"time": now, "role": role, "content": content}

    if wm is None:
        wm = WorkingMemory(
            user_id=user_id,
            session_id=session_id,
            date=today,
            entries=[entry],
            token_count=_count_tokens(content),
        )
        db.add(wm)
    else:
        entries = list(wm.entries or [])
        entries.append(entry)
        wm.entries = entries
        wm.token_count = sum(_count_tokens(e.get("content", "")) for e in entries)

    await db.commit()

    needs_compression = wm.token_count > _TOKEN_THRESHOLD
    if needs_compression:
        logger.info(
            "stm_compression_needed",
            user_id=str(user_id),
            tokens=wm.token_count,
        )
    return needs_compression


async def compress_working_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> str | None:
    """Compress today's STM into an archive summary using LLM.

    Moves entries to archive, resets STM to empty.
    Returns the summary text, or None if nothing to compress.
    """
    from app.llm.factory import create_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    today = date.today()
    result = await db.execute(
        select(WorkingMemory).where(
            and_(
                WorkingMemory.user_id == user_id,
                WorkingMemory.session_id == session_id,
                WorkingMemory.date == today,
            )
        )
    )
    wm = result.scalar_one_or_none()
    if wm is None or not wm.entries:
        return None

    entries_text = "\n".join(
        f"[{e.get('role', '?')}] {e.get('content', '')}" for e in wm.entries
    )

    llm = create_llm(purpose="fast")
    response = await llm.ainvoke([
        SystemMessage(content=(
            "Compress this conversation into a concise summary. "
            "Preserve key facts, decisions, and user preferences. "
            "Keep names, numbers, and specific details. "
            "Output only the summary, no preamble."
        )),
        HumanMessage(content=entries_text),
    ])
    summary = response.content.strip()

    # Save to archive
    archive = WorkingMemoryArchive(
        user_id=user_id,
        session_id=session_id,
        date=today,
        summary=summary,
        entries=wm.entries,
        embedded=False,
    )
    db.add(archive)

    # Reset STM
    wm.entries = []
    wm.token_count = 0

    await db.commit()
    logger.info("stm_compressed", user_id=str(user_id), summary_len=len(summary))
    return summary
