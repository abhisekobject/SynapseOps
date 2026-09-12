"""
SynapseOps Simulation — API Service.

Simulates the core API service that sits behind the gateway and in front
of the worker for background task dispatch.

Responsibilities:
- Handles incoming requests, optionally dispatching tasks to the worker.
- Tracks: requests/sec, error_rate, p50/p99 latency, memory_mb, active_connections.
- Applies failure effects: ERROR_RATE_SPIKE, MEMORY_PRESSURE, LATENCY, CRASH.

Realistic baseline behaviour:
- p50 latency: 15-40ms.
- p99 latency: 80-150ms.
- Error rate: ~0.2%.
- CPU: 5-15%.
- Memory: 120-200MB.
- Active connections: 30-100.

Run as standalone:
    uvicorn backend.simulation.services.api_service:app --port 8101
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any

from fastapi import FastAPI  # noqa: TC002
from redis.asyncio import Redis

from backend.simulation.models import FailureScenario, FailureTarget, FailureType
from backend.simulation.services.base import SimulatedServiceBase


class ApiService(SimulatedServiceBase):
    """Simulated core API service."""

    service_name = "sim-api"
    target = FailureTarget.API_SERVICE

    def __init__(self, redis_client: Redis, redis_failure_key: str = "sim:failures") -> None:
        super().__init__(redis_client=redis_client, redis_failure_key=redis_failure_key)
        self._active_connections: int = 0
        self._baseline_connections = random.randint(30, 100)
        # Memory starts at a realistic baseline and creeps up under MEMORY_PRESSURE
        self._baseline_memory_mb = random.uniform(120.0, 200.0)
        self._memory_growth_mb = 0.0
        self._startup_time = time.monotonic()

    async def _handle_request(self, path: str) -> dict[str, Any]:
        """Simulate API service logic.

        Baseline: 15-40ms processing time to simulate real API work
        (DB queries, serialization, etc.).
        """
        # Baseline processing time: 15-40ms
        baseline_ms = random.uniform(15.0, 40.0)
        await asyncio.sleep(baseline_ms / 1000.0)

        self._active_connections = max(0, self._baseline_connections + random.randint(-20, 20))

        return {
            "service": self.service_name,
            "path": path,
            "status": "ok",
            "processing_ms": round(baseline_ms, 2),
            "worker_dispatch": path.startswith("jobs") or path.startswith("tasks"),
        }

    def _build_custom_metrics(self, failures: list[FailureScenario]) -> dict[str, Any]:
        """API service telemetry.

        Memory grows under MEMORY_PRESSURE, CPU rises under request load.
        """
        base_cpu = random.uniform(5.0, 15.0)

        # CPU pressure from failure effects
        cpu_boost = sum(
            f.severity * 15.0
            for f in failures
            if f.failure_type in (FailureType.ERROR_RATE_SPIKE, FailureType.LATENCY)
        )
        cpu = min(100.0, base_cpu + cpu_boost)

        # Memory growth under MEMORY_PRESSURE — escalates over time
        memory_pressure = next(
            (f for f in failures if f.failure_type == FailureType.MEMORY_PRESSURE), None
        )
        if memory_pressure:
            # Memory grows at severity * 5 MB/second
            elapsed = time.monotonic() - self._startup_time
            self._memory_growth_mb = memory_pressure.severity * 5.0 * elapsed
        else:
            self._memory_growth_mb = 0.0

        memory_mb = min(
            self._baseline_memory_mb + self._memory_growth_mb,
            4096.0,  # Cap at 4GB for realism
        )

        return {
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(memory_mb, 2),
            "active_connections": self._active_connections,
            "queue_depth": None,
        }


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create the API service FastAPI application."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_key = os.getenv("SIM_FAILURE_REDIS_KEY", "sim:failures")

    redis_client = Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

    service = ApiService(redis_client=redis_client, redis_failure_key=redis_key)
    return service.build_app()


app = create_app()
