"""
SynapseOps Simulation -- Worker Service.

Simulates the background worker that processes jobs from a queue and
performs database-dependent operations.

Responsibilities:
- Processes simulated "jobs" from an in-memory queue.
- Tracks: queue_depth, job processing rate, cpu_percent, error_rate.
- Applies failure effects: CRASH, CPU_PRESSURE, DB_CONNECTION_EXHAUSTION,
  NETWORK_PARTITION, DOWNSTREAM_TIMEOUT.

Realistic baseline behaviour:
- Job processing rate: 10-30 jobs/second.
- Queue depth: 0-5 (drains quickly under normal load).
- p50 latency: 50-120ms (jobs require DB access).
- p99 latency: 200-400ms.
- CPU: 10-25%.
- Memory: 100-180MB.

Run as standalone:
    uvicorn backend.simulation.services.worker:app --port 8102
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import random
import time
from typing import Any

from fastapi import FastAPI  # noqa: TC002
from redis.asyncio import Redis

from backend.simulation.models import FailureScenario, FailureTarget, FailureType
from backend.simulation.services.base import SimulatedServiceBase


class WorkerService(SimulatedServiceBase):
    """Simulated background worker service."""

    service_name = "sim-worker"
    target = FailureTarget.WORKER

    def __init__(self, redis_client: Redis, redis_failure_key: str = "sim:failures") -> None:
        super().__init__(redis_client=redis_client, redis_failure_key=redis_failure_key)
        # Simulated job queue
        self._queue_depth: int = random.randint(0, 5)
        self._jobs_processed: int = 0
        self._startup_time = time.monotonic()
        # Background job processor task
        self._job_processor_task: asyncio.Task | None = None

    def build_app(self) -> FastAPI:
        """Override to also start the job processor background task."""
        app = super().build_app()

        @app.on_event("startup")
        async def _start_job_processor() -> None:
            self._job_processor_task = asyncio.create_task(
                self._job_processor_loop(),
                name="sim_worker_job_processor",
            )

        @app.on_event("shutdown")
        async def _stop_job_processor() -> None:
            if self._job_processor_task and not self._job_processor_task.done():
                self._job_processor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._job_processor_task

        return app

    async def _job_processor_loop(self) -> None:
        """Background loop that simulates job queue consumption.

        Under normal conditions: processes 1 job every 50-100ms.
        Under CPU_PRESSURE: 3-5x slower.
        Under CRASH: stops processing.
        Under DB_CONNECTION_EXHAUSTION or NETWORK_PARTITION: jobs
        either fail or get very slow.
        """
        while True:
            try:
                failures = await self._get_active_failures()

                # Add new jobs at a realistic rate (simulates incoming work)
                incoming = random.randint(1, 3)
                self._queue_depth = max(0, self._queue_depth + incoming)

                if any(f.failure_type == FailureType.CRASH for f in failures):
                    # Under crash: queue backs up, no processing
                    await asyncio.sleep(0.5)
                    continue

                # Determine processing rate based on failures
                base_interval_ms = random.uniform(50.0, 100.0)
                slowdown = 1.0
                for f in failures:
                    if f.failure_type == FailureType.CPU_PRESSURE:
                        slowdown += f.severity * 4.0  # 1.0 severity -> 5x slower
                    elif f.failure_type == FailureType.DB_CONNECTION_EXHAUSTION:
                        slowdown += f.severity * 3.0
                    elif f.failure_type == FailureType.NETWORK_PARTITION:
                        slowdown += f.severity * 6.0  # Very slow under partition
                    elif f.failure_type == FailureType.DOWNSTREAM_TIMEOUT:
                        slowdown += f.severity * 2.0

                interval = (base_interval_ms * slowdown) / 1000.0
                await asyncio.sleep(interval)

                # Process one job
                if self._queue_depth > 0:
                    self._queue_depth -= 1
                    self._jobs_processed += 1

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.5)

    async def _handle_request(self, path: str) -> dict[str, Any]:
        """Simulate worker API request handling.

        Workers expose an API for job submission and status queries.
        Processing time reflects queue state + DB access time.
        """
        failures = await self._get_active_failures()

        # Baseline: 50-120ms (DB-dependent work)
        baseline_ms = random.uniform(50.0, 120.0)

        # Under DB issues, add significant latency
        db_latency_ms = 0.0
        for f in failures:
            if f.failure_type == FailureType.DB_CONNECTION_EXHAUSTION:
                db_latency_ms += f.severity * 2000.0

        total_ms = baseline_ms + db_latency_ms
        await asyncio.sleep(total_ms / 1000.0)

        # Add a job to the queue when processing a job submission
        if path.startswith("jobs") and random.random() < 0.7:
            self._queue_depth = min(self._queue_depth + 1, 10000)

        return {
            "service": self.service_name,
            "path": path,
            "status": "ok",
            "queue_depth": self._queue_depth,
            "jobs_processed": self._jobs_processed,
            "processing_ms": round(total_ms, 2),
        }

    def _build_custom_metrics(self, failures: list[FailureScenario]) -> dict[str, Any]:
        """Worker-specific telemetry.

        CPU reflects processing load and CPU_PRESSURE failures.
        Queue depth reflects job accumulation under degraded conditions.
        """
        base_cpu = random.uniform(10.0, 25.0)
        base_mem = random.uniform(100.0, 180.0)

        cpu_boost = sum(
            f.severity * 65.0 for f in failures if f.failure_type == FailureType.CPU_PRESSURE
        )
        # Network partition also causes CPU overhead (retries, timeouts)
        cpu_boost += sum(
            f.severity * 15.0 for f in failures if f.failure_type == FailureType.NETWORK_PARTITION
        )
        cpu = min(100.0, base_cpu + cpu_boost)

        db_latency = random.uniform(50.0, 120.0)
        db_exhaustion = next(
            (f for f in failures if f.failure_type == FailureType.DB_CONNECTION_EXHAUSTION), None
        )
        if db_exhaustion:
            db_latency += db_exhaustion.severity * 2000.0

        return {
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(base_mem, 2),
            "active_connections": None,
            "queue_depth": self._queue_depth,
            "database_latency_ms": round(db_latency, 2),
        }


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create the worker service FastAPI application."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_key = os.getenv("SIM_FAILURE_REDIS_KEY", "sim:failures")

    redis_client = Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

    service = WorkerService(redis_client=redis_client, redis_failure_key=redis_key)
    return service.build_app()


app = create_app()
