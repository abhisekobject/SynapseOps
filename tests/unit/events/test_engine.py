import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.events.engine import EventEngine
from backend.events.models import Event, EventSeverity, EventType


@pytest.fixture
def event_engine():
    # Pass None for session_factory to skip persistence during unit tests
    return EventEngine(session_factory=None)


@pytest.mark.asyncio
async def test_event_engine_deduplication(event_engine):
    t1 = datetime.now(UTC)
    ev1 = Event(
        id=uuid.uuid4(),
        event_type=EventType.LATENCY_INCREASE,
        service_id="sim-api",
        severity=EventSeverity.WARNING,
        message="Warning",
        correlation_id="sim-api::latency_increase",
        created_at=t1,
        updated_at=t1,
    )

    # Process first proposal
    active = await event_engine.process_proposed_events("sim-api", [ev1])
    assert len(active) == 1
    assert active[0].id == ev1.id

    # Process second proposal for same condition
    t2 = t1 + timedelta(seconds=5)
    ev2 = Event(
        id=uuid.uuid4(),
        event_type=EventType.LATENCY_INCREASE,
        service_id="sim-api",
        severity=EventSeverity.WARNING,
        message="Warning still",
        correlation_id="sim-api::latency_increase",
        created_at=t2,
        updated_at=t2,
    )

    active2 = await event_engine.process_proposed_events("sim-api", [ev2])
    assert len(active2) == 1
    assert active2[0].id == ev1.id  # Kept the original event ID
    assert active2[0].updated_at == t2  # Updated the timestamp


@pytest.mark.asyncio
async def test_event_engine_severity_upgrade(event_engine):
    t1 = datetime.now(UTC)
    ev1 = Event(
        id=uuid.uuid4(),
        event_type=EventType.LATENCY_INCREASE,
        service_id="sim-api",
        severity=EventSeverity.WARNING,
        message="Warning",
        correlation_id="sim-api::latency_increase",
        created_at=t1,
        updated_at=t1,
    )
    await event_engine.process_proposed_events("sim-api", [ev1])

    t2 = t1 + timedelta(seconds=5)
    ev2 = Event(
        id=uuid.uuid4(),
        event_type=EventType.LATENCY_INCREASE,
        service_id="sim-api",
        severity=EventSeverity.CRITICAL,  # Escalated
        message="Critical",
        correlation_id="sim-api::latency_increase",
        created_at=t2,
        updated_at=t2,
    )

    active = await event_engine.process_proposed_events("sim-api", [ev2])
    assert len(active) == 1
    assert active[0].severity == EventSeverity.CRITICAL


@pytest.mark.asyncio
async def test_event_engine_clearing(event_engine):
    t1 = datetime.now(UTC)
    ev1 = Event(
        id=uuid.uuid4(),
        event_type=EventType.SERVICE_UNAVAILABLE,
        service_id="sim-worker",
        severity=EventSeverity.CRITICAL,
        message="Down",
        correlation_id="sim-worker::service_unavailable",
        created_at=t1,
        updated_at=t1,
    )
    await event_engine.process_proposed_events("sim-worker", [ev1])

    # Now it recovers
    t2 = t1 + timedelta(seconds=10)
    ev_recover = Event(
        id=uuid.uuid4(),
        event_type=EventType.SERVICE_AVAILABLE,
        service_id="sim-worker",
        severity=EventSeverity.INFO,
        message="Up",
        correlation_id="sim-worker::service_available",
        created_at=t2,
        updated_at=t2,
    )

    active = await event_engine.process_proposed_events("sim-worker", [ev_recover])
    assert len(active) == 0  # Should be cleared
