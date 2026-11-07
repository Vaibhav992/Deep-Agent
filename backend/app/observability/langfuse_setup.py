from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from app.config import get_settings

settings = get_settings()


def create_langfuse_handler(
    user_id: str, session_id: str, trace_name: str = "chat_turn"
) -> LangfuseCallbackHandler | None:
    """Create a LangFuse callback handler for LangGraph tracing.

    Returns None if LangFuse is not configured, so callers can
    skip it without branching.
    """
    if not settings.LANGFUSE_PUBLIC_KEY:
        return None

    return LangfuseCallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
        user_id=user_id,
        session_id=session_id,
        trace_name=trace_name,
        tags=["deep-agent", settings.APP_ENV],
    )
