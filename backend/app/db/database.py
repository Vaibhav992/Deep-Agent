from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import get_settings

settings = get_settings()

_connect_args = {}
if "neon.tech" in settings.DATABASE_URL or "sslmode" in settings.DATABASE_URL:
    _connect_args = {"server_settings": {"jit": "off"}}

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    # Pre-ping costs a full round trip per checkout (~1s from a distant client to Neon).
    # Recycling connections before Neon's idle timeout avoids stale connections without it.
    pool_pre_ping=False,
    pool_recycle=240,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a DB session per request."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
