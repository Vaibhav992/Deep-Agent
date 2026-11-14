"""Langfuse tracing for agent runs (Langfuse SDK v5).

The Langfuse client is configured once from settings. Each run gets a LangChain
CallbackHandler; user, session and tags travel in the run config's metadata.
With no Langfuse keys configured, every function is a no-op.
"""
from __future__ import annotations

from functools import lru_cache

import structlog
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

from app.config import get_settings

logger = structlog.get_logger()


@lru_cache
def _client() -> Langfuse | None:
    s = get_settings()
    if not (s.LANGFUSE_PUBLIC_KEY and s.LANGFUSE_SECRET_KEY):
        return None
    try:
        return Langfuse(public_key=s.LANGFUSE_PUBLIC_KEY, secret_key=s.LANGFUSE_SECRET_KEY, host=s.LANGFUSE_HOST)
    except Exception as e:
        logger.warning("langfuse_init_failed", error=str(e))
        return None


def langfuse_run_config(user_id: str, session_id: str, trace_name: str, metadata: dict | None = None) -> dict:
    """LangGraph run config that traces the run to Langfuse, or {} when Langfuse is off."""
    if _client() is None:
        return {}
    try:
        handler = CallbackHandler(public_key=get_settings().LANGFUSE_PUBLIC_KEY)
    except Exception as e:
        logger.warning("langfuse_handler_create_failed", error=str(e))
        return {}
    return {
        "callbacks": [handler],
        "run_name": trace_name,
        "metadata": {
            "langfuse_user_id": user_id,
            "langfuse_session_id": session_id,
            "langfuse_tags": ["deep-agent", get_settings().APP_ENV],
            **(metadata or {}),
        },
    }


def flush_langfuse() -> None:
    if _client() is None:
        return
    try:
        get_client().flush()
    except Exception as e:
        logger.warning("langfuse_flush_failed", error=str(e))
