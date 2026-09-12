from datetime import UTC, datetime

import pytest

from backend.core.config import Settings
from backend.events.engine import EventEngine
from backend.events.normalizer import TelemetryNormalizer
from backend.intelligence.anomaly import AnomalyDetector
from backend.state.engine import SystemStateEngine
from backend.state.models import ServiceStatus
from backend.telemetry.ingestion import TelemetryPoller
from backend.telemetry.models import TelemetrySnapshot


@pytest.fixture
def settings():
    return Settings(sim_health_poll_interval_seconds=1)




@pytest.fixture
def poller(settings):
    normalizer = TelemetryNormalizer(settings)
    anomaly_detector = AnomalyDetector(settings)
    event_engine = EventEngine(session_factory=None)
    state_engine = SystemStateEngine(settings, session_factory=None)
    return TelemetryPoller(settings, normalizer, anomaly_detector, event_engine, state_engine)


@pytest.mark.asyncio
async def test_process_snapshot(poller):
    snapshot = TelemetrySnapshot(
        service_id="sim-worker",
        timestamp=datetime.now(UTC),
        is_healthy=True,
        requests_per_second=10.5,
        error_rate_percent=0.0,
        p50_latency_ms=10.0,
        p99_latency_ms=20.0,
        queue_depth=5,
        active_failure_count=0,
    )

    await poller._run_pipeline(snapshot)

    snap = await poller.state_engine.get_system_snapshot()
    assert "sim-worker" in snap.services
    assert snap.services["sim-worker"].status == ServiceStatus.HEALTHY
    assert snap.services["sim-worker"].queue_depth == 5


@pytest.mark.asyncio
async def test_process_unavailable(poller):
    # Simulate an HTTP request error by calling _record_unavailable
    await poller._record_unavailable("sim-api")

    snap = await poller.state_engine.get_system_snapshot()
    assert "sim-api" in snap.services
    assert snap.services["sim-api"].status == ServiceStatus.UNAVAILABLE
