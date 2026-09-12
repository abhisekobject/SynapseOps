import asyncio
import contextlib
from datetime import UTC, datetime

import structlog

from backend.core.config import Settings
from backend.events.engine import EventEngine
from backend.events.normalizer import TelemetryNormalizer
from backend.intelligence.anomaly import AnomalyDetector
from backend.state.engine import SystemStateEngine
from backend.telemetry.models import TelemetrySnapshot
from backend.telemetry.prometheus import PrometheusTelemetryAdapter

logger = structlog.get_logger("telemetry.ingestion")


class TelemetryPoller:
    """Polls Prometheus for observability telemetry and drives the Phase 4 pipeline.

    This acts as the bridge between Phase 3 (Prometheus metrics) and Phase 4
    (normalized events and state).
    """

    def __init__(
        self,
        settings: Settings,
        normalizer: TelemetryNormalizer,
        anomaly_detector: AnomalyDetector,
        event_engine: EventEngine,
        state_engine: SystemStateEngine,
    ) -> None:
        self.settings = settings
        self.normalizer = normalizer
        self.anomaly_detector = anomaly_detector
        self.event_engine = event_engine
        self.state_engine = state_engine
        self._running = False
        self._task: asyncio.Task | None = None
        self._adapter = PrometheusTelemetryAdapter(settings)

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
        await self._adapter.close()
        logger.info("telemetry_poller_stopped")

    async def _poll_loop(self) -> None:
        # The services we monitor via Prometheus
        service_ids = ["sim-gateway", "sim-api", "sim-worker"]

        while self._running:
            try:
                # 1. Fetch telemetry
                for service_id in service_ids:
                    snapshot = await self._adapter.fetch_snapshot(service_id)
                    if snapshot:
                        await self._run_pipeline(snapshot)
                    else:
                        # If Prometheus cannot return metrics, we treat it as unavailable telemetry
                        await self._record_unavailable(service_id)

                # 2. Check for stale state across all services
                await self.state_engine.check_staleness()

            except Exception as exc:
                logger.error("telemetry_poller_error", detail=str(exc))

            await asyncio.sleep(self.settings.sim_health_poll_interval_seconds)

    async def _record_unavailable(self, service_id: str) -> None:
        """Process a failure to fetch telemetry (e.g. Prometheus down or target missing)."""
        now = datetime.now(UTC)
        snapshot = TelemetrySnapshot(
            service_id=service_id,
            timestamp=now,
            is_healthy=False,
            active_failure_count=0,
        )
        await self._run_pipeline(snapshot)

    async def _run_pipeline(self, snapshot: TelemetrySnapshot) -> None:
        """Run the normalized snapshot through the Phase 4 intelligence pipeline."""
        # 1. Normalize into proposed events
        proposed_events = self.normalizer.normalize(snapshot)

        # 1.5. Behavioral Anomaly Detection
        anomaly_events = await self.anomaly_detector.evaluate(snapshot)
        proposed_events.extend(anomaly_events)

        # 2. Deduplicate and correlate (Engine state machine)
        active_events = await self.event_engine.process_proposed_events(
            snapshot.service_id, proposed_events
        )

        # 3. Update coherent system state
        await self.state_engine.update_service_state(
            service_id=snapshot.service_id,
            active_events=active_events,
            telemetry_timestamp=snapshot.timestamp,
            p99_latency=snapshot.p99_latency_ms,
            error_rate=snapshot.error_rate_percent,
            queue_depth=snapshot.queue_depth,
        )
