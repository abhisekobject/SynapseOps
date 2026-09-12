"""
SynapseOps Simulation — Gateway Service.

Simulates an API gateway sitting in front of the API service.

Responsibilities:
- Receives incoming requests and "forwards" them to the API service.
- Tracks: requests/sec, error_rate, p50/p99 latency, active_connections.
- Applies failure effects: LATENCY, CASCADE_SLOW, ERROR_RATE_SPIKE, CRASH.

Realistic baseline behaviour:
- p50 latency: 8-15ms (gateway routing is fast).
- p99 latency: 30-60ms.
- Error rate: ~0.1% (very low under normal conditions).
- CPU: 3-8%.
- Memory: 50-80MB.
- Active connections: 20-80 (varies with simulated load).

Run as standalone:
    uvicorn backend.simulation.services.gateway:app --port 8100

Or via Docker Compose (see docker-compose.yml).
"""

from __future__ import annotations

import os
import random
import time
from typing import Any

from fastapi import FastAPI  # noqa: TC002
from redis.asyncio import Redis

from backend.simulation.models import FailureScenario, FailureType
from backend.simulation.services.base import SimulatedServiceBase

# ---------------------------------------------------------------------------
# Service implementation
# ---------------------------------------------------------------------------


class GatewayService(SimulatedServiceBase):
    """Simulated API gateway service."""

    service_name = "sim-gateway"

    from backend.simulation.models import FailureTarget

    target = __import__(
        "backend.simulation.models", fromlist=["FailureTarget"]
    ).FailureTarget.GATEWAY

    def __init__(self, redis_client: Redis, redis_failure_key: str = "sim:failures") -> None:
        super().__init__(redis_client=redis_client, redis_failure_key=redis_failure_key)
        self._active_connections: int = 0
        self._baseline_connections = random.randint(20, 80)
        self._startup_time = time.monotonic()

    async def _handle_request(self, path: str) -> dict[str, Any]:
        """Simulate gateway forwarding logic.

        Adds a small realistic baseline latency (8-15ms) to simulate
        the cost of routing + connection handling.
        """
        import asyncio

        # Baseline gateway latency: 8-15ms
        baseline_ms = random.uniform(8.0, 15.0)
        await asyncio.sleep(baseline_ms / 1000.0)

        # Simulate active connection count fluctuation
        self._active_connections = max(0, self._baseline_connections + random.randint(-10, 10))

        return {
            "service": self.service_name,
            "path": path,
            "status": "forwarded",
            "upstream": "sim-api:8101",
            "latency_ms": round(baseline_ms, 2),
        }

    def _build_custom_metrics(self, failures: list[FailureScenario]) -> dict[str, Any]:
        """Gateway-specific telemetry.

        CPU and memory reflect realistic gateway resource usage.
        Under LATENCY/CASCADE_SLOW, CPU rises slightly (buffering).
        """
        base_cpu = random.uniform(3.0, 8.0)
        base_mem = random.uniform(50.0, 80.0)

        cpu_boost = sum(
            f.severity * 10.0
            for f in failures
            if f.failure_type in (FailureType.LATENCY, FailureType.CASCADE_SLOW)
        )
        cpu = min(100.0, base_cpu + cpu_boost)

        return {
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(base_mem, 2),
            "active_connections": self._active_connections,
            "queue_depth": None,
        }


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create the gateway FastAPI application.

    Redis connection parameters are read from environment variables:
        REDIS_HOST (default: localhost)
        REDIS_PORT (default: 6379)
        REDIS_DB   (default: 0)
        SIM_FAILURE_REDIS_KEY (default: sim:failures)
    """
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_key = os.getenv("SIM_FAILURE_REDIS_KEY", "sim:failures")

    redis_client = Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

    service = GatewayService(redis_client=redis_client, redis_failure_key=redis_key)
    return service.build_app()


# Module-level app instance for uvicorn
app = create_app()
