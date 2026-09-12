from datetime import UTC, datetime

import pytest

from backend.core.config import Settings
from backend.events.models import EventSeverity, EventType
from backend.events.normalizer import TelemetryNormalizer
from backend.telemetry.models import TelemetrySnapshot


@pytest.fixture
def settings():
    return Settings(
        latency_warning_threshold_ms=300.0,
        latency_critical_threshold_ms=800.0,
        error_rate_warning_threshold=1.0,
        error_rate_critical_threshold=5.0,
        queue_warning_threshold=10,
        queue_critical_threshold=30,
    )


@pytest.fixture
def normalizer(settings):
    return TelemetryNormalizer(settings)


def test_normalize_healthy(normalizer):
    snapshot = TelemetrySnapshot(
        service_id="sim-api",
        timestamp=datetime.now(UTC),
        is_healthy=True,
        p99_latency_ms=150.0,
        error_rate_percent=0.0,
        queue_depth=0,
    )
    events = normalizer.normalize(snapshot)

    assert len(events) == 1
    assert events[0].event_type == EventType.SERVICE_AVAILABLE
    assert events[0].severity == EventSeverity.INFO


def test_normalize_latency_critical(normalizer):
    snapshot = TelemetrySnapshot(
        service_id="sim-api",
        timestamp=datetime.now(UTC),
        is_healthy=True,
        p99_latency_ms=900.0,  # Critical
    )
    events = normalizer.normalize(snapshot)

    assert any(
        e.event_type == EventType.LATENCY_INCREASE and e.severity == EventSeverity.CRITICAL
        for e in events
    )


def test_normalize_error_rate_warning(normalizer):
    snapshot = TelemetrySnapshot(
        service_id="sim-api",
        timestamp=datetime.now(UTC),
        is_healthy=True,
        error_rate_percent=2.5,  # Warning
    )
    events = normalizer.normalize(snapshot)

    assert any(
        e.event_type == EventType.ERROR_RATE_INCREASE and e.severity == EventSeverity.WARNING
        for e in events
    )


def test_normalize_unhealthy_and_failure(normalizer):
    snapshot = TelemetrySnapshot(
        service_id="sim-worker",
        timestamp=datetime.now(UTC),
        is_healthy=False,
        active_failure_count=1,
    )
    events = normalizer.normalize(snapshot)

    types = [e.event_type for e in events]
    assert EventType.SERVICE_UNAVAILABLE in types
    assert EventType.FAILURE_INJECTED in types
