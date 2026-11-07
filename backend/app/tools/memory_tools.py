"""Memory tools — search_memory and write_memory for the agent.

These are LangChain tools that the agent can call during research
to access and persist information across sessions.
"""
import uuid

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()


@tool
async def search_memory(query: str) -> str:
    """Search your memory for relevant past conversations and facts.

    Use this when the user references something from a previous
    conversation, or when historical context would help answer
    the current question.

    Args:
        query: What to search for in memory.

    Returns:
        Relevant memory context, or a message if nothing found.
    """
    # These are injected at runtime via the tool execution context
    from app.db.database import async_session
    from app.memory.vector_search import hybrid_search
    from app.memory.long_term_memory import get_ltm_for_context

    # Tool context: user_id is set by the researcher node
    user_id = search_memory._user_id
    if not user_id:
        return "[Error] No user context available for memory search."

    async with async_session() as db:
        # Search vector store + BM25
        results = await hybrid_search(db, query, user_id, k=5)

        # Also search LTM entries
        ltm_entries = await get_ltm_for_context(db, user_id)
        ltm_text = ""
        if ltm_entries:
            matching = [
                e for e in ltm_entries
                if any(word.lower() in e["content"].lower() for word in query.split())
            ]
            if matching:
                ltm_text = "\n\n**Long-term memories:**\n" + "\n".join(
                    f"- [{e['category']}] {e['content']}" for e in matching[:5]
                )

    if not results and not ltm_text:
        return f"No relevant memories found for: {query}"

    parts = []
    if results:
        parts.append("**From past conversations:**\n" + "\n\n---\n\n".join(results))
    if ltm_text:
        parts.append(ltm_text)

    return "\n\n".join(parts)

# Runtime user_id injection point
search_memory._user_id = None


@tool
async def write_memory(content: str, category: str = "fact") -> str:
    """Save an important fact or preference to long-term memory.

    Use this when the user tells you something important about
    themselves, their preferences, or facts they want you to remember.

    Args:
        content: The fact, preference, or rule to remember.
        category: One of 'fact', 'preference', 'rule', or 'skill'.

    Returns:
        Confirmation that the memory was saved.
    """
    from app.db.database import async_session
    from app.memory.long_term_memory import write_ltm

    user_id = write_memory._user_id
    session_id = write_memory._session_id
    if not user_id:
        return "[Error] No user context available for writing memory."

    valid = {"fact", "preference", "rule", "skill"}
    if category not in valid:
        category = "fact"

    async with async_session() as db:
        await write_ltm(
            db,
            user_id=user_id,
            category=category,
            content=content,
            session_id=session_id,
        )

    logger.info("memory_written_by_agent", category=category, content_len=len(content))
    return f"Memory saved: [{category}] {content}"

# Runtime context injection points
write_memory._user_id = None
write_memory._session_id = None
