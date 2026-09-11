"""
SynapseOps Redis Cache Layer.

Provides a minimal Redis client abstraction for Phase 1.
Redis is used for: short-lived state caching, future event queuing,
and background task coordination.

This module does NOT implement a full distributed queue or pub/sub system.
Those capabilities will be added in later phases only if requirements justify them.
"""

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from backend.core.config import Settings
from backend.core.logging import get_logger

logger = get_logger("cache.redis")


def create_redis_client(settings: Settings) -> Redis:
    """Create and return an async Redis client.

    Args:
        settings: Application settings containing Redis connection info.

    Returns:
        An async Redis client. Connection is lazy (established on first use).
    """
    logger.info(
        "Creating Redis client",
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


async def check_redis_connectivity(client: Redis) -> bool:
    """Ping Redis to verify connectivity.

    Args:
        client: The async Redis client.

    Returns:
        True if Redis responds to PING, False otherwise.

    Does not raise — returns False on any connectivity failure so that
    a Redis outage does not crash the health check or process startup.
    """
    try:
        await client.ping()
        logger.debug("Redis connectivity check passed")
        return True
    except RedisConnectionError as exc:
        logger.warning("Redis connectivity check failed", error=str(exc))
        return False
    except Exception as exc:
        logger.warning("Redis connectivity check failed (unexpected)", error=str(exc))
        return False


async def close_redis_client(client: Redis) -> None:
    """Close the Redis client connection pool gracefully.

    Args:
        client: The async Redis client to close.
    """
    await client.aclose()
    logger.info("Redis client closed")
