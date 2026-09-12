import asyncio
import contextlib
from datetime import UTC, datetime

import httpx
import structlog

from backend.core.config import Settings
from backend.events.engine import EventEngine
from backend.events.normalizer import TelemetryNormalizer
from backend.state.engine import SystemStateEngine
from backend.telemetry.models import TelemetrySnapshot

logger = structlog.get_logger("telemetry.ingestion")


class TelemetryPoller:
    """Polls simulation services for health telemetry and drives the Phase 4 pipeline.

    This acts as the bridge between Phase 2/3 (raw simulation/telemetry) and Phase 4
    (normalized events and state).
    """

    def __init__(
        self,
        settings: Settings,
        normalizer: TelemetryNormalizer,
        event_engine: EventEngine,
        state_engine: SystemStateEngine,
    ) -> None:
        self.settings = settings
        self.normalizer = normalizer
        self.event_engine = event_engine
        self.state_engine = state_engine
        self._running = False
        self._task: asyncio.Task | None = None
        self._client = httpx.AsyncClient(timeout=2.0)

    def start(self) -> None:
        """Start the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "telemetry_poller_started",
            interval_seconds=self.settings.sim_health_poll_interval_seconds,
        )

    async def stop(self) -> None:
        """Stop the background polling loop."""
        self._running = False

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self._client.aclose()
        logger.info("telemetry_poller_stopped")

    async def _poll_loop(self) -> None:
        # We need to poll the 3 simulation endpoints
        endpoints = [
            ("sim-gateway", f"{self.settings.sim_gateway_url}/health"),
            ("sim-api", f"{self.settings.sim_api_url}/health"),
            ("sim-worker", f"{self.settings.sim_worker_url}/health"),
        ]

        while self._running:
            try:
                # 1. Fetch telemetry
                for service_id, url in endpoints:
                    try:
                        response = await self._client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            await self._process_snapshot(service_id, data)
                        else:
                            # Service responded but not 200 OK - possibly failure injection
                            try:
                                data = response.json()
                                # Simulation /health doesn't return 500/503 for normal health checks usually,
                                # but if it does, we can try to parse.
                                await self._process_snapshot(service_id, data)
                            except Exception:
                                self._record_unavailable(service_id)
                    except httpx.RequestError:
                        self._record_unavailable(service_id)

                # 2. Check for stale state across all services
                self.state_engine.check_staleness()

            except Exception as exc:
                logger.error("telemetry_poller_error", detail=str(exc))

            await asyncio.sleep(self.settings.sim_health_poll_interval_seconds)

    async def _process_snapshot(self, expected_service_id: str, data: dict) -> None:
        """Process a successful ServiceHealthSnapshot into the Phase 4 pipeline."""
        now = datetime.now(UTC)

        # Convert to our generic TelemetrySnapshot
        # Some fields might be None (e.g. gateway doesn't have queue_depth)
        snapshot = TelemetrySnapshot(
            service_id=data.get("service_name", expected_service_id),
            timestamp=now,
            requests_per_second=data.get("requests_per_second"),
            error_rate_percent=data.get("error_rate_percent"),
            p50_latency_ms=data.get("p50_latency_ms"),
            p99_latency_ms=data.get("p99_latency_ms"),
            cpu_percent=data.get("cpu_percent"),
            memory_mb=data.get("memory_mb"),
            queue_depth=data.get("queue_depth"),
            is_healthy=data.get("status") == "healthy",
            active_failure_count=len(data.get("active_failure_types", [])),
        )

        self._run_pipeline(snapshot)

    def _record_unavailable(self, service_id: str) -> None:
        """Process a hard network failure (cannot reach simulation service at all)."""
        now = datetime.now(UTC)
        snapshot = TelemetrySnapshot(
            service_id=service_id,
            timestamp=now,
            is_healthy=False,
            active_failure_count=0,
        )
        self._run_pipeline(snapshot)

    def _run_pipeline(self, snapshot: TelemetrySnapshot) -> None:
        """Run the normalized snapshot through the Phase 4 intelligence pipeline."""
        # 1. Normalize into proposed events
        proposed_events = self.normalizer.normalize(snapshot)

        # 2. Deduplicate and correlate (Engine state machine)
        active_events = self.event_engine.process_proposed_events(
            snapshot.service_id, proposed_events
        )

        # 3. Update coherent system state
        self.state_engine.update_service_state(
            service_id=snapshot.service_id,
            active_events=active_events,
            telemetry_timestamp=snapshot.timestamp,
            p99_latency=snapshot.p99_latency_ms,
            error_rate=snapshot.error_rate_percent,
            queue_depth=snapshot.queue_depth,
        )
