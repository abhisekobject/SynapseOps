from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.events.models import Event, EventStatus, EventType
from backend.models.db.event import EventORM

logger = structlog.get_logger("events.engine")


class EventEngine:
    """Manages the lifecycle of operational events via deterministic deduplication.

    This engine receives proposed events from the TelemetryNormalizer.
    It maintains an in-memory active list. If a condition persists (same correlation_id),
    it updates the existing event. If a condition clears, it marks the event CLEARED.
    It now uses SQLAlchemy to durably persist events.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._active_events: dict[str, Event] = {}
        self._session_factory = session_factory

    async def _persist_event(self, ev: Event) -> None:
        """Persist an event to the database."""
        if not self._session_factory:
            return
        async with self._session_factory() as session:
            try:
                # Upsert by ID (or just insert since we generate IDs and only update in-memory)
                # For Phase 4, we'll fetch existing or create new
                db_event = await session.get(EventORM, ev.id)
                if not db_event:
                    db_event = EventORM(id=ev.id)
                    session.add(db_event)

                db_event.event_type = ev.event_type
                db_event.service_id = ev.service_id
                db_event.severity = ev.severity
                db_event.status = ev.status
                db_event.message = ev.message
                db_event.correlation_id = ev.correlation_id
                db_event.trace_id = ev.trace_id
                db_event.evidence = ev.evidence
                if ev.status == EventStatus.CLEARED:
                    db_event.resolved_at = ev.updated_at

                await session.commit()
            except Exception as exc:
                logger.error("failed_to_persist_event", error=str(exc))

    async def process_proposed_events(self, service_id: str, proposed_events: list[Event]) -> list[Event]:
        """Process new proposals, returning the updated list of currently active events for the service."""

        incoming_correlation_ids = set()

        for proposed in proposed_events:
            if proposed.correlation_id is None:
                continue

            # Special case: FAILURE_CLEARED clears FAILURE_INJECTED
            if proposed.event_type == EventType.FAILURE_CLEARED:
                inj_corr_id = f"{service_id}::{EventType.FAILURE_INJECTED.value}"
                if inj_corr_id in self._active_events:
                    await self._clear_event(inj_corr_id, proposed.updated_at)
                continue

            incoming_correlation_ids.add(proposed.correlation_id)

            if proposed.event_type == EventType.SERVICE_AVAILABLE:
                unavail_corr_id = f"{service_id}::{EventType.SERVICE_UNAVAILABLE.value}"
                if unavail_corr_id in self._active_events:
                    await self._clear_event(unavail_corr_id, proposed.updated_at)
                continue

            if proposed.correlation_id in self._active_events:
                existing = self._active_events[proposed.correlation_id]
                existing.updated_at = proposed.updated_at
                existing.evidence = proposed.evidence
                if self._severity_weight(proposed.severity) > self._severity_weight(existing.severity):
                    existing.severity = proposed.severity
                    existing.message = proposed.message
                await self._persist_event(existing)
            else:
                self._active_events[proposed.correlation_id] = proposed
                logger.info(
                    "event_created",
                    event_id=str(proposed.id),
                    event_type=proposed.event_type,
                    service_id=service_id,
                    severity=proposed.severity,
                )
                await self._persist_event(proposed)

        cleared_ids = []
        for corr_id, active_event in self._active_events.items():
            if active_event.service_id != service_id:
                continue
            if corr_id not in incoming_correlation_ids:
                cleared_ids.append(corr_id)

        for corr_id in cleared_ids:
            clear_time = proposed_events[0].updated_at if proposed_events else None
            await self._clear_event(corr_id, clear_time)

        return [e for e in self._active_events.values() if e.service_id == service_id]

    def get_all_active_events(self) -> list[Event]:
        """Return all active events across all services."""
        return list(self._active_events.values())

    async def _clear_event(self, correlation_id: str, clear_time: Any = None) -> None:
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
            await self._persist_event(ev)

    def _severity_weight(self, severity: str) -> int:
        from backend.events.models import EventSeverity
        if severity == EventSeverity.INFO:
            return 1
        if severity == EventSeverity.WARNING:
            return 2
        if severity == EventSeverity.CRITICAL:
            return 3
        return 0
