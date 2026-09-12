import collections
import statistics
from uuid import uuid4

import structlog

from backend.core.config import Settings
from backend.events.models import Event, EventSeverity, EventStatus, EventType
from backend.telemetry.models import TelemetrySnapshot

logger = structlog.get_logger("intelligence.anomaly")


class SignalHistory:
    """Maintains the rolling history and anomaly state for a single signal of a service."""

    def __init__(self, max_length: int) -> None:
        self.values: collections.deque[float] = collections.deque(maxlen=max_length)
        self.consecutive_anomalies: int = 0
        self.is_active: bool = False
        self.active_severity: EventSeverity | None = None
        self.active_message: str | None = None
        self.active_evidence: dict[str, float] = {}


class AnomalyDetector:
    """Detects behavioral anomalies in telemetry using deterministic statistical baselines (Phase 5)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # mapping: service_id -> (signal_name -> SignalHistory)
        self._history: dict[str, dict[str, SignalHistory]] = collections.defaultdict(
            lambda: collections.defaultdict(
                lambda: SignalHistory(max_length=self.settings.anomaly_window_size)
            )
        )

        self._signal_map = {
            "cpu_percent": EventType.ANOMALY_CPU,
            "memory_mb": EventType.ANOMALY_MEMORY,
            "p99_latency_ms": EventType.ANOMALY_LATENCY,
            "error_rate_percent": EventType.ANOMALY_ERROR_RATE,
            "queue_depth": EventType.ANOMALY_QUEUE,
            "database_latency_ms": EventType.ANOMALY_DATABASE_LATENCY,
        }

    async def evaluate(self, snapshot: TelemetrySnapshot) -> list[Event]:
        """Evaluate a snapshot against established behavioral baselines and return anomalous events."""
        proposed_events: list[Event] = []

        for signal_name, event_type in self._signal_map.items():
            current_value = getattr(snapshot, signal_name, None)
            history = self._history[snapshot.service_id][signal_name]

            # 1. Missing Telemetry Handling
            if current_value is None:
                if history.is_active and history.active_severity and history.active_message:
                    # Retain the active anomaly to prevent false recovery.
                    proposed_events.append(
                        self._create_event(
                            snapshot=snapshot,
                            event_type=event_type,
                            severity=history.active_severity,
                            message=f"[Stale Telemetry] {history.active_message}",
                            evidence=history.active_evidence,
                        )
                    )
                continue

            # 2. Cold Start Handling
            if len(history.values) < self.settings.anomaly_min_samples:
                history.values.append(current_value)
                history.consecutive_anomalies = 0
                history.is_active = False
                continue

            # 3. Baseline Calculation (using historical window before adding current value)
            mean = statistics.mean(history.values)
            stddev = statistics.pstdev(history.values)

            # Safely add current value to rolling history
            history.values.append(current_value)

            # 4. Deviation & Threshold Evaluation
            severity = None
            z_score = None
            deviation = abs(current_value - mean)

            if stddev == 0.0:
                # Zero Variance Handling
                if deviation >= self.settings.anomaly_absolute_fallback * (
                    self.settings.anomaly_z_critical / self.settings.anomaly_z_warning
                ):
                    severity = EventSeverity.CRITICAL
                elif deviation >= self.settings.anomaly_absolute_fallback:
                    severity = EventSeverity.WARNING
            else:
                z_score = deviation / stddev
                if z_score >= self.settings.anomaly_z_critical:
                    severity = EventSeverity.CRITICAL
                elif z_score >= self.settings.anomaly_z_warning:
                    severity = EventSeverity.WARNING

            # 5. Noise Suppression & Lifecycle Updates
            if severity:
                history.consecutive_anomalies += 1
                if history.consecutive_anomalies >= self.settings.anomaly_activation_consecutive:
                    # Activate / Retain
                    history.is_active = True
                    history.active_severity = severity

                    if z_score is not None:
                        msg = f"Behavioral anomaly: {signal_name} deviates significantly from baseline. Z-score: {z_score:.2f} (mean: {mean:.2f}, stddev: {stddev:.2f})"
                    else:
                        msg = f"Behavioral anomaly: {signal_name} deviates absolutely from zero-variance baseline. Deviation: {deviation:.2f} (mean: {mean:.2f})"

                    history.active_message = msg

                    evidence = {"observed_value": current_value, "baseline_mean": mean}
                    if z_score is not None:
                        evidence["z_score"] = z_score

                    history.active_evidence = evidence

                    proposed_events.append(
                        self._create_event(
                            snapshot=snapshot,
                            event_type=event_type,
                            severity=severity,
                            message=msg,
                            evidence=evidence,
                        )
                    )
            else:
                # Normal behavior -> Recover
                history.consecutive_anomalies = 0
                history.is_active = False
                history.active_severity = None
                history.active_message = None
                history.active_evidence = {}

        return proposed_events

    def _create_event(
        self,
        snapshot: TelemetrySnapshot,
        event_type: EventType,
        severity: EventSeverity,
        message: str,
        evidence: dict[str, float],
    ) -> Event:
        # Deterministic correlation ID ensures EventEngine can deduplicate anomalies properly
        correlation_id = f"{snapshot.service_id}::{event_type.value}"

        return Event(
            id=uuid4(),
            event_type=event_type,
            service_id=snapshot.service_id,
            severity=severity,
            status=EventStatus.ACTIVE,
            message=message,
            correlation_id=correlation_id,
            created_at=snapshot.timestamp,
            updated_at=snapshot.timestamp,
            evidence=evidence,
        )
