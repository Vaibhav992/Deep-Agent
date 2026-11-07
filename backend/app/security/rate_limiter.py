from fastapi import Depends, HTTPException, status
import redis.asyncio as aioredis

from app.config import get_settings
from app.db.redis import get_redis

settings = get_settings()


async def check_rate_limit(
    user_id: str,
    redis: aioredis.Redis = Depends(get_redis),
    limit: int | None = None,
):
    """Sliding-window rate limiter using Redis INCR + EXPIRE.

    Checks per-user request count in a 60-second window.
    Raises 429 if limit exceeded.
    """
    max_requests = limit or settings.RATE_LIMIT_PER_MINUTE
    key = f"ratelimit:{user_id}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)

    if count > max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {max_requests} requests per minute.",
        )
