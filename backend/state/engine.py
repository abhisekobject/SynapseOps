from datetime import UTC, datetime

import structlog

from backend.core.config import Settings
from backend.events.models import Event, EventType
from backend.state.models import ServiceState, ServiceStatus, SystemSnapshot

logger = structlog.get_logger("state.engine")


class SystemStateEngine:
    """Maintains the latest operational state for all known services.

    This engine receives the list of deduplicated active events for a service
    and determines the deterministic overall status (HEALTHY, DEGRADED, UNAVAILABLE).
    It also enforces stale-state policies (UNKNOWN).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._services: dict[str, ServiceState] = {}

    def update_service_state(
        self,
        service_id: str,
        active_events: list[Event],
        telemetry_timestamp: datetime,
        p99_latency: float | None = None,
        error_rate: float | None = None,
        queue_depth: int | None = None,
    ) -> ServiceState:
        """Update a service's state based on fresh telemetry and active events."""

        # Determine status deterministically from active events
        new_status = ServiceStatus.HEALTHY

        has_unavailable = any(e.event_type == EventType.SERVICE_UNAVAILABLE for e in active_events)
        has_critical = any(e.severity == "critical" for e in active_events)
        has_warning = any(e.severity == "warning" for e in active_events)

        if has_unavailable:
            new_status = ServiceStatus.UNAVAILABLE
        elif has_critical or has_warning:
            # For this phase, any warning/critical performance issue degrades the service.
            new_status = ServiceStatus.DEGRADED

        # Get or create state tracking
        if service_id not in self._services:
            self._services[service_id] = ServiceState(
                service_id=service_id,
                status=new_status,
                last_seen=telemetry_timestamp,
                last_state_change=telemetry_timestamp,
                active_event_ids=[str(e.id) for e in active_events],
            )
            logger.info("service_discovered", service_id=service_id, status=new_status)

        state = self._services[service_id]

        # Check for status transitions
        if state.status != new_status:
            logger.info(
                "state_transition",
                service_id=service_id,
                old_status=state.status,
                new_status=new_status,
            )
            state.status = new_status
            state.last_state_change = telemetry_timestamp

        # Update telemetry
        state.last_seen = telemetry_timestamp
        state.active_event_ids = [str(e.id) for e in active_events]
        if p99_latency is not None:
            state.latency_p99_ms = p99_latency
        if error_rate is not None:
            state.error_rate_percent = error_rate
        if queue_depth is not None:
            state.queue_depth = queue_depth

        return state

    def check_staleness(self, now: datetime | None = None) -> None:
        """Scan all services and mark them UNKNOWN if telemetry is stale."""
        if now is None:
            now = datetime.now(UTC)

        for service_id, state in self._services.items():
            if state.status == ServiceStatus.UNKNOWN:
                continue

            age_seconds = (now - state.last_seen).total_seconds()
            if age_seconds > self.settings.state_staleness_seconds:
                logger.warning(
                    "state_stale",
                    service_id=service_id,
                    last_seen=state.last_seen.isoformat(),
                    age_seconds=round(age_seconds, 1),
                )
                state.status = ServiceStatus.UNKNOWN
                state.last_state_change = now

    def get_system_snapshot(self) -> SystemSnapshot:
        """Generate a point-in-time snapshot of the entire system."""
        # Ensure staleness is applied before generating snapshot
        now = datetime.now(UTC)
        self.check_staleness(now)

        overall = ServiceStatus.HEALTHY
        total_active_events = 0

        for state in self._services.values():
            if state.status == ServiceStatus.UNAVAILABLE:
                overall = ServiceStatus.UNAVAILABLE
            elif state.status == ServiceStatus.DEGRADED and overall != ServiceStatus.UNAVAILABLE:
                overall = ServiceStatus.DEGRADED
            elif state.status == ServiceStatus.UNKNOWN and overall == ServiceStatus.HEALTHY:
                # If everything else is healthy but something is unknown, we are degraded
                overall = ServiceStatus.DEGRADED

            total_active_events += len(state.active_event_ids)

        return SystemSnapshot(
            timestamp=now,
            overall_status=overall,
            active_event_count=total_active_events,
            critical_event_count=0,  # Could be derived if we keep event severity in memory state
            services=self._services.copy(),
        )
