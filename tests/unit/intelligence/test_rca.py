import uuid
from datetime import UTC, datetime, timedelta

from backend.events.models import Event, EventSeverity, EventStatus, EventType
from backend.intelligence.graph import DependencyGraph
from backend.intelligence.rca import RCAEngine


def make_event(
    event_type: EventType,
    service_id: str,
    severity: EventSeverity,
    minutes_ago: int,
) -> Event:
    now = datetime.now(UTC)
    t = now - timedelta(minutes=minutes_ago)
    return Event(
        id=uuid.uuid4(),
        event_type=event_type,
        service_id=service_id,
        severity=severity,
        message="Test event",
        status=EventStatus.ACTIVE,
        correlation_id=f"{service_id}::{event_type}",
        created_at=t,
        updated_at=t,
    )


class TestRCAEngine:
    def test_database_latency_cascade(self):
        """Scenario A: DB -> Worker -> API -> Gateway cascade"""
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.ANOMALY_DATABASE_LATENCY, "sim-worker", EventSeverity.CRITICAL, 10),
            make_event(EventType.LATENCY_INCREASE, "sim-worker", EventSeverity.WARNING, 8),
            make_event(EventType.ANOMALY_LATENCY, "sim-api", EventSeverity.WARNING, 6),
            make_event(EventType.ANOMALY_LATENCY, "sim-gateway", EventSeverity.WARNING, 4),
        ]

        result = engine.analyze(events, window_minutes=15)
        assert len(result.candidates) == 4

        # DB should be ranked highest (highest score due to cascade origin + severity)
        top = result.candidates[0]
        assert top.component == "database"
        assert top.confidence in ["HIGH", "MEDIUM"]

        # Verify affected components propagated down
        assert "sim-worker" in top.affected_components
        assert "sim-api" in top.affected_components
        assert "sim-gateway" in top.affected_components

    def test_worker_crash(self):
        """Scenario B: Worker crashes -> API -> Gateway cascade"""
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.SERVICE_UNAVAILABLE, "sim-worker", EventSeverity.CRITICAL, 5),
            make_event(EventType.ANOMALY_ERROR_RATE, "sim-api", EventSeverity.WARNING, 3),
            make_event(EventType.ANOMALY_ERROR_RATE, "sim-gateway", EventSeverity.WARNING, 1),
        ]

        result = engine.analyze(events, window_minutes=15)
        top = result.candidates[0]
        assert top.component == "sim-worker"
        assert "sim-api" in top.affected_components

    def test_independent_anomalies(self):
        """Scenario D: Independent anomalies (DB and Redis degraded simultaneously)"""
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.ANOMALY_DATABASE_LATENCY, "sim-worker", EventSeverity.WARNING, 2),
            make_event(EventType.ANOMALY_LATENCY, "redis", EventSeverity.WARNING, 2),
        ]

        result = engine.analyze(events)
        assert len(result.candidates) == 2
        # No propagation should be registered between them
        assert len(result.candidates[0].affected_components) == 0
        assert len(result.candidates[1].affected_components) == 0

    def test_downstream_only(self):
        """Scenario F: API anomaly with healthy dependencies"""
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.ANOMALY_ERROR_RATE, "sim-api", EventSeverity.CRITICAL, 2),
        ]

        result = engine.analyze(events)
        assert len(result.candidates) == 1
        top = result.candidates[0]
        assert top.component == "sim-api"
        # It should lose score points because it has no affected downstream victims? Actually it might, wait.
        # But it should be the only candidate.

    def test_deterministic_tie_breaker(self):
        """Verify sorting handles identical scores deterministically."""
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.ANOMALY_CPU, "sim-api", EventSeverity.WARNING, 2),
            make_event(EventType.ANOMALY_CPU, "sim-worker", EventSeverity.WARNING, 2),
        ]

        # sim-api and sim-worker have same exact severity, no precedence over each other (not cascading since same time).
        # Should break tie alphabetically
        result = engine.analyze(events)
        assert result.candidates[0].component == "sim-api"
        assert result.candidates[1].component == "sim-worker"

    def test_redis_degradation(self):
        """Scenario C: Redis degradation -> Worker cascade"""
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.ANOMALY_LATENCY, "redis", EventSeverity.WARNING, 5),
            make_event(EventType.ANOMALY_LATENCY, "sim-worker", EventSeverity.WARNING, 3),
        ]

        result = engine.analyze(events, window_minutes=15)
        top = result.candidates[0]
        assert top.component == "redis"
        assert "sim-worker" in top.affected_components

    def test_missing_telemetry(self):
        """Scenario G: Missing telemetry"""
        # Missing telemetry does not fabricate events, but Phase 5 emits [Stale Telemetry] events.
        # It's just a regular event that stays ACTIVE.
        graph = DependencyGraph()
        engine = RCAEngine(graph)

        events = [
            make_event(EventType.ANOMALY_CPU, "sim-worker", EventSeverity.CRITICAL, 10),
            # Telemetry goes missing, so anomaly stays active (updated_at keeps moving forward in Phase 5).
        ]

        result = engine.analyze(events, window_minutes=15)
        top = result.candidates[0]
        assert top.component == "sim-worker"
        assert len(top.affected_components) == 0

