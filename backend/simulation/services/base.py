"""
SynapseOps Simulation — Base Service.

Provides SimulatedServiceBase: the shared foundation for all simulated
services (gateway, api_service, worker).

Architecture:
    Each simulated service is a standalone FastAPI application that:
    1. Reads its active failure scenarios from Redis on a background poll loop.
    2. Applies failure effects to every request based on those scenarios.
    3. Maintains in-memory telemetry counters (request counts, error counts,
       latency histogram buckets, resource metrics).
    4. Exposes:
        GET /health  — ServiceHealthSnapshot (JSON)
        GET /metrics — Prometheus text format

Failure effect mapping (by FailureType):
    CRASH               -> 503 on all non-/health requests
    ERROR_RATE_SPIKE    -> HTTP 500 on severity*80% of requests
    LATENCY             -> add severity*2000ms to every request
    CPU_PRESSURE        -> add severity*1500ms delay; report cpu_percent approx severity*100
    MEMORY_PRESSURE     -> escalate memory_mb report over time
    DB_CONNECTION_EXHAUSTION -> add latency + occasional 500s on DB ops
    NETWORK_PARTITION   -> downstream calls return timeout error
    DISK_IO_PRESSURE    -> add delay to I/O; report in metrics
    DOWNSTREAM_TIMEOUT  -> downstream calls time out after 2s
    CASCADE_SLOW        -> add latency (same as LATENCY but labeled separately)

Design notes:
    - All effects are applied in-process (no actual subprocess spawning).
    - Telemetry values are realistic, not random — they reflect the configured
      severity and current failure state.
    - The health endpoint always responds (even during CRASH) so that
      SynapseOps can observe the service's reported status.
    - asyncio.sleep() is used for latency injection; this is realistic because
      it frees the event loop (models I/O wait, not CPU burn).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import os
import random
import time
from collections import deque
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis  # noqa: TC002

from backend.simulation.models import (
    FailureScenario,
    FailureTarget,
    FailureType,
    ServiceHealthSnapshot,
)

_sim_logger = logging.getLogger(__name__)


def _setup_otel_for_service(app: FastAPI, service_name: str) -> None:
    """Attach OpenTelemetry tracing to a simulated service FastAPI app.

    Uses standard OTel env vars so each service gets its own identity:
        OTEL_SERVICE_NAME=synapseops-gateway  (set in docker-compose)
        OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

    Fail-safe: any exception during setup is logged and suppressed;
    the service continues to operate without tracing.
    """
    if os.getenv("OTEL_ENABLED", "true").lower() in ("false", "0", "no"):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME as OTEL_SERVICE_NAME
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        resource = Resource.create({OTEL_SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() != "false",
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        _sim_logger.info("OTel tracing enabled for %s -> %s", service_name, endpoint)
    except Exception as exc:
        _sim_logger.warning(
            "OTel setup failed for %s (%s); continuing without tracing",
            service_name,
            exc,
        )


# ---------------------------------------------------------------------------
# Telemetry helpers
# ---------------------------------------------------------------------------

_LATENCY_WINDOW = 100  # rolling window size for latency percentile estimates


class LatencyTracker:
    """Rolling window latency tracker for p50/p99 computation.

    Uses a fixed-size deque of recent latency samples (milliseconds).
    Fast enough for a development simulator; not meant for production.
    """

    def __init__(self, window: int = _LATENCY_WINDOW) -> None:
        self._samples: deque[float] = deque(maxlen=window)

    def record(self, latency_ms: float) -> None:
        self._samples.append(latency_ms)

    def p50(self) -> float | None:
        if not self._samples:
            return None
        sorted_samples = sorted(self._samples)
        idx = math.floor(len(sorted_samples) * 0.50)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def p95(self) -> float | None:
        if not self._samples:
            return None
        sorted_samples = sorted(self._samples)
        idx = math.floor(len(sorted_samples) * 0.95)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def p99(self) -> float | None:
        if not self._samples:
            return None
        sorted_samples = sorted(self._samples)
        idx = math.floor(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]


# ---------------------------------------------------------------------------
# Base service class
# ---------------------------------------------------------------------------


class SimulatedServiceBase:
    """Base class for all simulated services.

    Subclasses override:
        - `service_name`: string identifier
        - `target`: FailureTarget enum value for this service
        - `_handle_request()`: core request logic (called after failure effects)
        - Any custom telemetry fields in `_build_custom_metrics()`

    Usage in a subclass:
        class GatewayService(SimulatedServiceBase):
            service_name = "sim-gateway"
            target = FailureTarget.GATEWAY

            async def _handle_request(self, path: str) -> dict:
                ...
    """

    service_name: str = "sim-base"
    target: FailureTarget = FailureTarget.ALL

    def __init__(self, redis_client: Redis, redis_failure_key: str = "sim:failures") -> None:
        self._redis = redis_client
        self._redis_failure_key = redis_failure_key

        # Active failure scenarios (refreshed periodically from Redis)
        self._active_failures: list[FailureScenario] = []
        self._failures_lock = asyncio.Lock()

        # Telemetry counters
        self._request_count: int = 0
        self._error_count: int = 0
        self._latency_tracker = LatencyTracker()
        self._start_time: float = time.monotonic()

        # Background task
        self._poll_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # FastAPI app factory
    # ------------------------------------------------------------------

    def build_app(self) -> FastAPI:
        """Build and return the FastAPI application for this service."""
        app = FastAPI(
            title=self.service_name,
            description=f"SynapseOps simulated service: {self.service_name}",
            version="0.1.0",
            docs_url="/docs",
            redoc_url=None,
        )

        # Phase 3: Attach OTel tracing using the service's canonical name
        _setup_otel_for_service(app, f"synapseops-{self.service_name}")

        @app.on_event("startup")
        async def _startup() -> None:
            self._start_time = time.monotonic()
            self.start_poll_task()

        @app.on_event("shutdown")
        async def _shutdown() -> None:
            await self.stop()

        @app.get("/health", response_model=ServiceHealthSnapshot, tags=["observability"])
        async def health() -> ServiceHealthSnapshot:
            """Service health and telemetry snapshot."""
            return await self._build_health_snapshot()

        @app.get("/metrics", response_class=Response, tags=["observability"])
        async def metrics() -> Response:
            """Prometheus text format metrics."""
            return Response(
                content=await self._build_prometheus_metrics(),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )

        @app.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            include_in_schema=False,
        )
        async def catch_all(path: str, request: Request) -> JSONResponse:
            """Handle all other routes with failure effect simulation."""
            return await self._dispatch(path=path, request=request)

        return app

    # ------------------------------------------------------------------
    # Failure state polling
    # ------------------------------------------------------------------

    def start_poll_task(self) -> None:
        """Start the background task that polls Redis for failure state."""
        if self._poll_task and not self._poll_task.done():
            return
        self._poll_task = asyncio.create_task(
            self._poll_loop(), name=f"{self.service_name}_failure_poll"
        )

    async def stop(self) -> None:
        """Cancel the background polling task."""
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task

    async def _poll_loop(self) -> None:
        """Poll Redis every 2 seconds to refresh active failure state."""
        while True:
            try:
                await self._refresh_failures()
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception:
                # Never crash the poll loop; just wait and retry
                await asyncio.sleep(2.0)

    async def _refresh_failures(self) -> None:
        """Read the current failure state from Redis and filter for this service."""
        try:
            raw = await self._redis.get(self._redis_failure_key)
            if raw:
                data = json.loads(raw)
                scenarios = [FailureScenario.model_validate(d) for d in data]
                relevant = [
                    s
                    for s in scenarios
                    if s.active and (s.target == self.target or s.target == FailureTarget.ALL)
                ]
            else:
                relevant = []

            async with self._failures_lock:
                self._active_failures = relevant
        except Exception:
            # On Redis errors, keep current failure state
            pass

    async def _get_active_failures(self) -> list[FailureScenario]:
        async with self._failures_lock:
            return list(self._active_failures)

    # ------------------------------------------------------------------
    # Request dispatch with failure effects
    # ------------------------------------------------------------------

    async def _dispatch(self, path: str, request: Request) -> JSONResponse:
        """Apply failure effects and dispatch to _handle_request."""
        failures = await self._get_active_failures()
        self._request_count += 1
        start = time.monotonic()

        # 1. CRASH — return 503 immediately (no further processing)
        if any(f.failure_type == FailureType.CRASH for f in failures):
            self._error_count += 1
            return JSONResponse(
                status_code=503,
                content={
                    "error": "service_unavailable",
                    "service": self.service_name,
                    "detail": "Service is in CRASH failure mode.",
                },
            )

        # 2. Latency injection (LATENCY, CASCADE_SLOW, CPU_PRESSURE)
        total_delay_ms = 0.0
        for f in failures:
            if f.failure_type in (FailureType.LATENCY, FailureType.CASCADE_SLOW):
                total_delay_ms += f.severity * 2000.0
            elif f.failure_type == FailureType.CPU_PRESSURE:
                total_delay_ms += f.severity * 1500.0
            elif f.failure_type == FailureType.DB_CONNECTION_EXHAUSTION:
                total_delay_ms += f.severity * 3000.0
            elif f.failure_type in (FailureType.DOWNSTREAM_TIMEOUT, FailureType.NETWORK_PARTITION):
                total_delay_ms += f.severity * 2000.0

        if total_delay_ms > 0:
            # Add a small jitter (±10%) to make it realistic
            jitter = random.uniform(-0.1, 0.1) * total_delay_ms
            delay = max(0.0, total_delay_ms + jitter) / 1000.0
            await asyncio.sleep(delay)

        # 3. ERROR_RATE_SPIKE — probabilistic 500
        for f in failures:
            if f.failure_type == FailureType.ERROR_RATE_SPIKE:
                error_probability = f.severity * 0.8  # severity 1.0 → 80% error rate
                if random.random() < error_probability:
                    self._error_count += 1
                    elapsed = (time.monotonic() - start) * 1000
                    self._latency_tracker.record(elapsed)
                    return JSONResponse(
                        status_code=500,
                        content={
                            "error": "internal_server_error",
                            "service": self.service_name,
                            "detail": "Simulated error rate spike.",
                        },
                    )

        # 4. NETWORK_PARTITION — downstream calls fail
        for f in failures:
            if f.failure_type == FailureType.NETWORK_PARTITION:
                self._error_count += 1
                elapsed = (time.monotonic() - start) * 1000
                self._latency_tracker.record(elapsed)
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "network_partition",
                        "service": self.service_name,
                        "detail": "Cannot reach downstream dependency (network partition).",
                    },
                )

        # 5. Delegate to subclass handler
        try:
            result = await self._handle_request(path=path)
            elapsed = (time.monotonic() - start) * 1000
            self._latency_tracker.record(elapsed)
            return JSONResponse(status_code=200, content=result)
        except Exception as exc:
            self._error_count += 1
            elapsed = (time.monotonic() - start) * 1000
            self._latency_tracker.record(elapsed)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "service": self.service_name,
                    "detail": str(exc),
                },
            )

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    async def _handle_request(self, path: str) -> dict[str, Any]:
        """Subclasses override this to provide service-specific logic.

        Returns a JSON-serialisable dict that becomes the response body.
        """
        return {"service": self.service_name, "path": path, "status": "ok"}

    def _compute_rps(self) -> float:
        """Estimate requests per second since startup."""
        uptime = time.monotonic() - self._start_time
        if uptime < 1.0:
            return 0.0
        return self._request_count / uptime

    def _compute_error_rate(self) -> float:
        """Compute error rate as a percentage."""
        if self._request_count == 0:
            return 0.0
        return (self._error_count / self._request_count) * 100.0

    # ------------------------------------------------------------------
    # Health and metrics
    # ------------------------------------------------------------------

    async def _build_health_snapshot(self) -> ServiceHealthSnapshot:
        """Build the health/telemetry snapshot for the /health endpoint."""
        failures = await self._get_active_failures()
        active_types = [f.failure_type for f in failures]
        is_crashed = FailureType.CRASH in active_types

        custom = self._build_custom_metrics(failures)

        status = "crashed" if is_crashed else ("degraded" if failures else "healthy")

        return ServiceHealthSnapshot(
            service_name=self.service_name,
            status=status,
            active_failure_types=[str(t) for t in active_types],
            requests_per_second=round(self._compute_rps(), 2),
            error_rate_percent=round(self._compute_error_rate(), 2),
            p50_latency_ms=self._latency_tracker.p50(),
            p95_latency_ms=self._latency_tracker.p95(),
            p99_latency_ms=self._latency_tracker.p99(),
            **custom,
        )

    def _build_custom_metrics(self, failures: list[FailureScenario]) -> dict[str, Any]:
        """Subclasses override to add service-specific telemetry fields.

        Returns a dict of keyword arguments compatible with ServiceHealthSnapshot.
        """
        return {}

    async def _build_prometheus_metrics(self) -> str:
        """Build Prometheus text-format metrics string."""
        failures = await self._get_active_failures()
        custom = self._build_custom_metrics(failures)

        rps = self._compute_rps()
        error_rate = self._compute_error_rate()
        p50 = self._latency_tracker.p50() or 0.0
        p95 = self._latency_tracker.p95() or 0.0
        p99 = self._latency_tracker.p99() or 0.0
        cpu = custom.get("cpu_percent") or 0.0
        mem = custom.get("memory_mb") or 0.0
        conns = custom.get("active_connections") or 0
        queue = custom.get("queue_depth") or 0
        db_lat = custom.get("database_latency_ms") or 0.0
        is_healthy = 0 if failures else 1

        svc = self.service_name.replace("-", "_")
        lines = [
            f"# HELP {svc}_requests_per_second Requests handled per second",
            f"# TYPE {svc}_requests_per_second gauge",
            f"{svc}_requests_per_second {rps:.4f}",
            f"# HELP {svc}_error_rate_percent Percentage of requests resulting in errors",
            f"# TYPE {svc}_error_rate_percent gauge",
            f"{svc}_error_rate_percent {error_rate:.4f}",
            f"# HELP {svc}_request_latency_p50_ms p50 request latency in milliseconds",
            f"# TYPE {svc}_request_latency_p50_ms gauge",
            f"{svc}_request_latency_p50_ms {p50:.4f}",
            f"# HELP {svc}_request_latency_p95_ms p95 request latency in milliseconds",
            f"# TYPE {svc}_request_latency_p95_ms gauge",
            f"{svc}_request_latency_p95_ms {p95:.4f}",
            f"# HELP {svc}_request_latency_p99_ms p99 request latency in milliseconds",
            f"# TYPE {svc}_request_latency_p99_ms gauge",
            f"{svc}_request_latency_p99_ms {p99:.4f}",
            f"# HELP {svc}_cpu_percent Simulated CPU utilisation percentage",
            f"# TYPE {svc}_cpu_percent gauge",
            f"{svc}_cpu_percent {cpu:.4f}",
            f"# HELP {svc}_memory_mb Simulated memory usage in megabytes",
            f"# TYPE {svc}_memory_mb gauge",
            f"{svc}_memory_mb {mem:.4f}",
            f"# HELP {svc}_active_connections Active connection count",
            f"# TYPE {svc}_active_connections gauge",
            f"{svc}_active_connections {conns}",
            f"# HELP {svc}_queue_depth Job queue depth",
            f"# TYPE {svc}_queue_depth gauge",
            f"{svc}_queue_depth {queue}",
            f"# HELP {svc}_database_latency_ms Simulated database query latency in ms",
            f"# TYPE {svc}_database_latency_ms gauge",
            f"{svc}_database_latency_ms {db_lat:.4f}",
            f"# HELP {svc}_healthy 1 if service is healthy (no active failures), else 0",
            f"# TYPE {svc}_healthy gauge",
            f"{svc}_healthy {is_healthy}",
            f"# HELP {svc}_active_failure_count Number of active failures",
            f"# TYPE {svc}_active_failure_count gauge",
            f"{svc}_active_failure_count {len(failures)}",
            f"# HELP {svc}_total_requests Total requests handled since startup",
            f"# TYPE {svc}_total_requests counter",
            f"{svc}_total_requests {self._request_count}",
            f"# HELP {svc}_total_errors Total errors since startup",
            f"# TYPE {svc}_total_errors counter",
            f"{svc}_total_errors {self._error_count}",
        ]
        return "\n".join(lines) + "\n"
