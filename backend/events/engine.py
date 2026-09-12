from typing import Any

import structlog

from backend.events.models import Event, EventStatus, EventType

logger = structlog.get_logger("events.engine")


class EventEngine:
    """Manages the lifecycle of operational events via deterministic deduplication.

    This engine receives proposed events from the TelemetryNormalizer.
    It maintains an in-memory active list. If a condition persists (same correlation_id),
    it updates the existing event. If a condition clears, it marks the event CLEARED.

    Currently uses an in-memory dictionary. A distributed system would back this with Redis.
    """

    def __init__(self) -> None:
        # Map of correlation_id -> Event
        self._active_events: dict[str, Event] = {}

    def process_proposed_events(self, service_id: str, proposed_events: list[Event]) -> list[Event]:
        """Process new proposals, returning the updated list of currently active events for the service."""

        # 1. Deduplicate/update incoming active conditions
        incoming_correlation_ids = set()

        for proposed in proposed_events:
            if proposed.correlation_id is None:
                continue

            incoming_correlation_ids.add(proposed.correlation_id)

            # Special case: SERVICE_AVAILABLE implies clearing SERVICE_UNAVAILABLE
            if proposed.event_type == EventType.SERVICE_AVAILABLE:
                # We do not store SERVICE_AVAILABLE as an active state.
                # It just acts as a clearing signal for SERVICE_UNAVAILABLE.
                unavail_corr_id = f"{service_id}::{EventType.SERVICE_UNAVAILABLE.value}"
                if unavail_corr_id in self._active_events:
                    self._clear_event(unavail_corr_id, proposed.updated_at)
                continue

            if proposed.correlation_id in self._active_events:
                # Update existing active event (extend its duration, update evidence)
                existing = self._active_events[proposed.correlation_id]
                existing.updated_at = proposed.updated_at
                existing.evidence = proposed.evidence
                # If severity worsened, upgrade it
                if self._severity_weight(proposed.severity) > self._severity_weight(
                    existing.severity
                ):
                    existing.severity = proposed.severity
                    existing.message = proposed.message
            else:
                # New condition emerged
                self._active_events[proposed.correlation_id] = proposed
                logger.info(
                    "event_created",
                    event_id=str(proposed.id),
                    event_type=proposed.event_type,
                    service_id=service_id,
                    severity=proposed.severity,
                )

        # 2. Find conditions that have cleared
        # A condition has cleared if we were tracking it for this service, but it's not in the new proposals.
        # We only check event types that are expected to be continuously reported.
        # Exceptions: FAILURE_INJECTED is reported as long as active_failure_count > 0.

        cleared_ids = []
        for corr_id, active_event in self._active_events.items():
            if active_event.service_id != service_id:
                continue  # Only check events for the service currently being processed

            # If it's not in the incoming proposals, and it's not something permanent, clear it.
            if corr_id not in incoming_correlation_ids:
                cleared_ids.append(corr_id)

        for corr_id in cleared_ids:
            # We use the timestamp of the first proposal (if any) as the clearance time,
            # or just now if no proposals were sent (e.g. perfectly healthy).
            clear_time = proposed_events[0].updated_at if proposed_events else None
            self._clear_event(corr_id, clear_time)

        # Return all currently active events for this service
        return [e for e in self._active_events.values() if e.service_id == service_id]

    def get_all_active_events(self) -> list[Event]:
        """Return all active events across all services."""
        return list(self._active_events.values())

    def _clear_event(self, correlation_id: str, clear_time: Any = None) -> None:
        """Mark an event as cleared and remove it from active tracking."""
        if correlation_id in self._active_events:
            ev = self._active_events.pop(correlation_id)
            ev.status = EventStatus.CLEARED
            if clear_time:
                ev.updated_at = clear_time
            logger.info(
                "event_cleared",
                event_id=str(ev.id),
                event_type=ev.event_type,
                service_id=ev.service_id,
            )
            # In a full implementation, we would persist this cleared event to the DB here.

    def _severity_weight(self, severity: str) -> int:
        from backend.events.models import EventSeverity

        if severity == EventSeverity.INFO:
            return 1
        if severity == EventSeverity.WARNING:
            return 2
        if severity == EventSeverity.CRITICAL:
            return 3
        return 0
