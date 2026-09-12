from datetime import UTC, datetime

import pytest

from backend.core.config import Settings
from backend.events.models import EventSeverity, EventType
from backend.intelligence.anomaly import AnomalyDetector
from backend.telemetry.models import TelemetrySnapshot


@pytest.fixture
def settings():
    # Make cold start quick for testing
    return Settings(
        anomaly_window_size=10,
        anomaly_min_samples=3,
        anomaly_z_warning=2.0,
        anomaly_z_critical=3.0,
        anomaly_activation_consecutive=2,
        anomaly_absolute_fallback=1.0,
    )


@pytest.fixture
def detector(settings):
    return AnomalyDetector(settings)


def make_snapshot(cpu: float = 50.0, timestamp: datetime | None = None, **kwargs) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        service_id="sim-worker",
        timestamp=timestamp or datetime.now(UTC),
        is_healthy=True,
        cpu_percent=cpu,
        **kwargs
    )


@pytest.mark.asyncio
async def test_cold_start_ignores_initial_samples(detector):
    # Min samples is 3
    events = await detector.evaluate(make_snapshot(50.0))
    assert len(events) == 0

    events = await detector.evaluate(make_snapshot(51.0))
    assert len(events) == 0


@pytest.mark.asyncio
async def test_stable_telemetry_does_not_trigger_anomaly(detector):
    for i in range(10):
        events = await detector.evaluate(make_snapshot(50.0 + (i % 2)))
        assert len(events) == 0


@pytest.mark.asyncio
async def test_anomaly_activation_and_noise_suppression(detector):
    # 1. Warm up baseline (mean = 50.0, stddev = 0)
    for _ in range(10):
        await detector.evaluate(make_snapshot(50.0))

    # 2. First anomalous sample (consecutive = 1) -> No event proposed yet (noise suppression)
    events = await detector.evaluate(make_snapshot(900.0))
    assert len(events) == 0

    # 3. Second anomalous sample (consecutive = 2) -> Activates
    events = await detector.evaluate(make_snapshot(900.0))
    assert len(events) == 1
    assert events[0].event_type == EventType.ANOMALY_CPU
    assert events[0].severity == EventSeverity.CRITICAL


@pytest.mark.asyncio
async def test_zero_variance_fallback(detector):
    detector.settings.anomaly_activation_consecutive = 1

    for _ in range(10):
        await detector.evaluate(make_snapshot(50.0))

    # Absolute deviation = 1.2. Fallback warning = 1.0. Critical = 1.5.
    events = await detector.evaluate(make_snapshot(51.2))

    assert len(events) == 1
    assert events[0].severity == EventSeverity.WARNING


@pytest.mark.asyncio
async def test_recovery_clears_anomaly(detector):
    for _ in range(10):
        await detector.evaluate(make_snapshot(50.0))

    # Activate anomaly
    await detector.evaluate(make_snapshot(900.0))
    events = await detector.evaluate(make_snapshot(900.0))
    assert len(events) == 1

    # Recovery
    events = await detector.evaluate(make_snapshot(50.0))
    assert len(events) == 0


@pytest.mark.asyncio
async def test_missing_telemetry_retains_active_anomaly(detector):
    # Setup baseline
    for _ in range(10):
        await detector.evaluate(make_snapshot(cpu=50.0, memory_mb=200.0))

    # Activate anomaly for CPU
    await detector.evaluate(make_snapshot(cpu=900.0, memory_mb=200.0))
    events = await detector.evaluate(make_snapshot(cpu=900.0, memory_mb=200.0))
    assert len(events) == 1
    assert events[0].event_type == EventType.ANOMALY_CPU

    # Now missing CPU telemetry (None), but memory is present.
    # The anomaly should be retained.
    events = await detector.evaluate(make_snapshot(cpu=None, memory_mb=200.0))
    assert len(events) == 1
    assert events[0].event_type == EventType.ANOMALY_CPU
    assert "[Stale Telemetry]" in events[0].message
