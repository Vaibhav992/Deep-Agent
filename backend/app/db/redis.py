"""Redis client supporting both local Redis and Upstash Redis.

Local dev: uses standard redis-py with REDIS_URL (redis://localhost:6379/0)
Production (Upstash): uses upstash-redis HTTP SDK with UPSTASH_REDIS_REST_URL + TOKEN
"""
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

_redis_client = None


def _create_upstash_client():
    """Create Upstash Redis client (HTTP-based, serverless-friendly)."""
    from upstash_redis.asyncio import Redis
    return Redis(
        url=settings.UPSTASH_REDIS_REST_URL,
        token=settings.UPSTASH_REDIS_REST_TOKEN,
    )


def _create_local_client():
    """Create standard redis-py async client (for local dev)."""
    import redis.asyncio as aioredis
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )
    return aioredis.Redis(connection_pool=pool)


def get_redis_client():
    """Get or create the Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            _redis_client = _create_upstash_client()
            logger.info("redis_connected", provider="upstash")
        else:
            _redis_client = _create_local_client()
            logger.info("redis_connected", provider="local")
    return _redis_client


redis_client = get_redis_client()


async def get_redis():
    """FastAPI dependency for Redis access."""
    return get_redis_client()
