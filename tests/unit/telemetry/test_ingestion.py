import pytest

from backend.core.config import Settings
from backend.events.engine import EventEngine
from backend.events.normalizer import TelemetryNormalizer
from backend.state.engine import SystemStateEngine
from backend.state.models import ServiceStatus
from backend.telemetry.ingestion import TelemetryPoller


@pytest.fixture
def settings():
    return Settings(sim_health_poll_interval_seconds=1)


@pytest.fixture
def poller(settings):
    normalizer = TelemetryNormalizer(settings)
    event_engine = EventEngine()
    state_engine = SystemStateEngine(settings)
    return TelemetryPoller(settings, normalizer, event_engine, state_engine)


@pytest.mark.asyncio
async def test_process_snapshot(poller):
    data = {
        "service_name": "sim-worker",
        "status": "healthy",
        "requests_per_second": 10.5,
        "error_rate_percent": 0.0,
        "p50_latency_ms": 10.0,
        "p99_latency_ms": 20.0,
        "queue_depth": 5,
        "active_failure_types": [],
    }

    await poller._process_snapshot("sim-worker", data)

    snap = poller.state_engine.get_system_snapshot()
    assert "sim-worker" in snap.services
    assert snap.services["sim-worker"].status == ServiceStatus.HEALTHY
    assert snap.services["sim-worker"].queue_depth == 5


@pytest.mark.asyncio
async def test_process_unavailable(poller):
    # Simulate an HTTP request error by calling _record_unavailable
    poller._record_unavailable("sim-api")

    snap = poller.state_engine.get_system_snapshot()
    assert "sim-api" in snap.services
    assert snap.services["sim-api"].status == ServiceStatus.UNAVAILABLE
