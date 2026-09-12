import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.core.config import Settings
from backend.events.models import Event, EventSeverity, EventType
from backend.state.engine import SystemStateEngine
from backend.state.models import ServiceStatus


@pytest.fixture
def settings():
    return Settings(state_staleness_seconds=15)


@pytest.fixture
def state_engine(settings):
    return SystemStateEngine(settings)


def _make_event(event_type: EventType, severity: EventSeverity):
    return Event(
        id=uuid.uuid4(),
        event_type=event_type,
        service_id="sim-gateway",
        severity=severity,
        message="Test event",
        correlation_id=f"sim-gateway::{event_type.value}",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_state_engine_healthy(state_engine):
    t1 = datetime.now(UTC)
    state = state_engine.update_service_state("sim-gateway", [], t1)

    assert state.status == ServiceStatus.HEALTHY
    assert state.last_seen == t1
    assert len(state.active_event_ids) == 0


def test_state_engine_degraded(state_engine):
    t1 = datetime.now(UTC)
    ev = _make_event(EventType.LATENCY_INCREASE, EventSeverity.WARNING)

    state = state_engine.update_service_state("sim-gateway", [ev], t1)
    assert state.status == ServiceStatus.DEGRADED


def test_state_engine_unavailable(state_engine):
    t1 = datetime.now(UTC)
    ev_latency = _make_event(EventType.LATENCY_INCREASE, EventSeverity.WARNING)
    ev_down = _make_event(EventType.SERVICE_UNAVAILABLE, EventSeverity.CRITICAL)

    # Unavailable takes precedence
    state = state_engine.update_service_state("sim-gateway", [ev_latency, ev_down], t1)
    assert state.status == ServiceStatus.UNAVAILABLE


def test_state_engine_staleness(state_engine):
    t1 = datetime.now(UTC) - timedelta(seconds=20)

    # Update state 20 seconds ago
    state_engine.update_service_state("sim-gateway", [], t1)

    # Check staleness now
    now = datetime.now(UTC)
    state_engine.check_staleness(now)

    snap = state_engine.get_system_snapshot()
    assert snap.services["sim-gateway"].status == ServiceStatus.UNKNOWN
