"""Async Redis client (used for rate-limiter state and pub/sub).

For the hackathon scope, Redis is intentionally lightweight: we use it for
rate-limiter token-bucket state and (optionally) pub/sub fan-out. The
EventBus remains in-process; Redis is not the queue.
"""

from __future__ import annotations

import redis.asyncio as redis

from backend.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the lazily-initialized Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the singleton client on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
