from uuid import uuid4

from backend.core.config import Settings
from backend.events.models import Event, EventSeverity, EventStatus, EventType
from backend.telemetry.models import TelemetrySnapshot


class TelemetryNormalizer:
    """Normalizes raw telemetry snapshots into proposed operational events.

    This engine uses strictly deterministic rules configured by application settings.
    It does not perform anomaly detection (Phase 5) or root cause analysis (Phase 6).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def normalize(self, snapshot: TelemetrySnapshot) -> list[Event]:
        """Convert a single telemetry snapshot into a list of proposed events."""
        events: list[Event] = []

        # 1. Health checks
        if not snapshot.is_healthy:
            # If it's unhealthy but has no active failures, we treat it as UNAVAILABLE.
            # If it has active failures, the failure controller might have just degraded it.
            # We map explicit health failure to a SERVICE_UNAVAILABLE event.
            events.append(
                self._create_event(
                    snapshot,
                    EventType.SERVICE_UNAVAILABLE,
                    EventSeverity.CRITICAL,
                    f"Service {snapshot.service_id} is reporting unhealthy status.",
                )
            )
        else:
            events.append(
                self._create_event(
                    snapshot,
                    EventType.SERVICE_AVAILABLE,
                    EventSeverity.INFO,
                    f"Service {snapshot.service_id} is available.",
                )
            )

        # 2. Latency checks
        if snapshot.p99_latency_ms is not None:
            if snapshot.p99_latency_ms >= self.settings.latency_critical_threshold_ms:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.LATENCY_INCREASE,
                        EventSeverity.CRITICAL,
                        f"Critical p99 latency: {snapshot.p99_latency_ms}ms (threshold: {self.settings.latency_critical_threshold_ms}ms)",
                    )
                )
            elif snapshot.p99_latency_ms >= self.settings.latency_warning_threshold_ms:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.LATENCY_INCREASE,
                        EventSeverity.WARNING,
                        f"Warning p99 latency: {snapshot.p99_latency_ms}ms (threshold: {self.settings.latency_warning_threshold_ms}ms)",
                    )
                )

        # 3. Error Rate checks
        if snapshot.error_rate_percent is not None:
            if snapshot.error_rate_percent >= self.settings.error_rate_critical_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.ERROR_RATE_INCREASE,
                        EventSeverity.CRITICAL,
                        f"Critical error rate: {snapshot.error_rate_percent}% (threshold: {self.settings.error_rate_critical_threshold}%)",
                    )
                )
            elif snapshot.error_rate_percent >= self.settings.error_rate_warning_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.ERROR_RATE_INCREASE,
                        EventSeverity.WARNING,
                        f"Warning error rate: {snapshot.error_rate_percent}% (threshold: {self.settings.error_rate_warning_threshold}%)",
                    )
                )

        # 4. Queue Depth checks
        if snapshot.queue_depth is not None:
            if snapshot.queue_depth >= self.settings.queue_critical_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.QUEUE_DEPTH_INCREASE,
                        EventSeverity.CRITICAL,
                        f"Critical queue depth: {snapshot.queue_depth} (threshold: {self.settings.queue_critical_threshold})",
                    )
                )
            elif snapshot.queue_depth >= self.settings.queue_warning_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.QUEUE_DEPTH_INCREASE,
                        EventSeverity.WARNING,
                        f"Warning queue depth: {snapshot.queue_depth} (threshold: {self.settings.queue_warning_threshold})",
                    )
                )

        # 5. CPU checks
        if snapshot.cpu_percent is not None:
            if snapshot.cpu_percent >= self.settings.cpu_critical_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.CPU_PRESSURE,
                        EventSeverity.CRITICAL,
                        f"Critical CPU usage: {snapshot.cpu_percent}% (threshold: {self.settings.cpu_critical_threshold}%)",
                    )
                )
            elif snapshot.cpu_percent >= self.settings.cpu_warning_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.CPU_PRESSURE,
                        EventSeverity.WARNING,
                        f"Warning CPU usage: {snapshot.cpu_percent}% (threshold: {self.settings.cpu_warning_threshold}%)",
                    )
                )

        # 6. Memory checks
        if snapshot.memory_mb is not None:
            if snapshot.memory_mb >= self.settings.memory_critical_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.MEMORY_PRESSURE,
                        EventSeverity.CRITICAL,
                        f"Critical Memory usage: {snapshot.memory_mb}MB (threshold: {self.settings.memory_critical_threshold}MB)",
                    )
                )
            elif snapshot.memory_mb >= self.settings.memory_warning_threshold:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.MEMORY_PRESSURE,
                        EventSeverity.WARNING,
                        f"Warning Memory usage: {snapshot.memory_mb}MB (threshold: {self.settings.memory_warning_threshold}MB)",
                    )
                )

        # 6.5. Database Latency checks
        if snapshot.database_latency_ms is not None:
            if snapshot.database_latency_ms >= self.settings.db_latency_critical_threshold_ms:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.DATABASE_LATENCY_INCREASE,
                        EventSeverity.CRITICAL,
                        f"Critical Database latency: {snapshot.database_latency_ms}ms (threshold: {self.settings.db_latency_critical_threshold_ms}ms)",
                    )
                )
            elif snapshot.database_latency_ms >= self.settings.db_latency_warning_threshold_ms:
                events.append(
                    self._create_event(
                        snapshot,
                        EventType.DATABASE_LATENCY_INCREASE,
                        EventSeverity.WARNING,
                        f"Warning Database latency: {snapshot.database_latency_ms}ms (threshold: {self.settings.db_latency_warning_threshold_ms}ms)",
                    )
                )

        # 7. Failure Injection checks (bridging from simulation directly)
        if snapshot.active_failure_count > 0:
            events.append(
                self._create_event(
                    snapshot,
                    EventType.FAILURE_INJECTED,
                    EventSeverity.CRITICAL,
                    f"Service {snapshot.service_id} has {snapshot.active_failure_count} active injected failures.",
                )
            )
        else:
            # Explicitly emit FAILURE_CLEARED if no failures are active.
            events.append(
                self._create_event(
                    snapshot,
                    EventType.FAILURE_CLEARED,
                    EventSeverity.INFO,
                    f"Service {snapshot.service_id} has no active injected failures.",
                )
            )

        return events

    def _create_event(
        self,
        snapshot: TelemetrySnapshot,
        event_type: EventType,
        severity: EventSeverity,
        message: str,
    ) -> Event:
        # Correlation ID strategy: A deterministic string representing the condition
        correlation_id = f"{snapshot.service_id}::{event_type.value}"

        # Collect relevant evidence to store in the event
        evidence = {}
        if snapshot.p99_latency_ms is not None:
            evidence["p99_latency_ms"] = snapshot.p99_latency_ms
        if snapshot.error_rate_percent is not None:
            evidence["error_rate_percent"] = snapshot.error_rate_percent
        if snapshot.queue_depth is not None:
            evidence["queue_depth"] = snapshot.queue_depth
        if snapshot.database_latency_ms is not None:
            evidence["database_latency_ms"] = snapshot.database_latency_ms
        evidence["is_healthy"] = snapshot.is_healthy
        evidence["active_failure_count"] = snapshot.active_failure_count

        return Event(
            id=uuid4(),
            event_type=event_type,
            service_id=snapshot.service_id,
            severity=severity,
            status=EventStatus.ACTIVE,
            message=message,
            correlation_id=correlation_id,
            trace_id=None,  # Telemetry ingestion runs out-of-band of request context
            created_at=snapshot.timestamp,
            updated_at=snapshot.timestamp,
            evidence=evidence,
        )
