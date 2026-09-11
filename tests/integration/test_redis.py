"""
Integration tests — Redis connectivity.

These tests require a running Redis instance.
Run with: pytest tests/integration/ -v -m integration

Skip in CI/unit-only runs: pytest tests/unit/ -v
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires running Redis — run manually with docker-compose up")
class TestRedisConnectivity:
    """Integration tests for Redis connectivity.

    Prerequisites:
        docker-compose up -d redis
        # or a running Redis instance matching .env settings
    """

    async def test_redis_ping_succeeds(self, test_settings):
        """Verify that the Redis client can ping the server."""
        from backend.cache.redis import (
            check_redis_connectivity,
            close_redis_client,
            create_redis_client,
        )

        client = create_redis_client(test_settings)
        try:
            result = await check_redis_connectivity(client)
            assert result is True
        finally:
            await close_redis_client(client)

    async def test_redis_set_and_get(self, test_settings):
        """Verify basic set/get operations work."""
        from backend.cache.redis import close_redis_client, create_redis_client

        client = create_redis_client(test_settings)
        try:
            await client.set("synapseops:test:key", "test_value", ex=10)
            value = await client.get("synapseops:test:key")
            assert value == "test_value"
            await client.delete("synapseops:test:key")
        finally:
            await close_redis_client(client)
