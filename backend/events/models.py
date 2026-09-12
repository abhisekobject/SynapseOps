from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Normalized operational event types."""

    SERVICE_AVAILABLE = "service_available"
    SERVICE_UNAVAILABLE = "service_unavailable"

    LATENCY_INCREASE = "latency_increase"
    ERROR_RATE_INCREASE = "error_rate_increase"
    QUEUE_DEPTH_INCREASE = "queue_depth_increase"

    CPU_PRESSURE = "cpu_pressure"
    MEMORY_PRESSURE = "memory_pressure"
    DATABASE_LATENCY_INCREASE = "database_latency_increase"

    FAILURE_INJECTED = "failure_injected"
    FAILURE_CLEARED = "failure_cleared"

    # Phase 5 Anomaly Types
    ANOMALY_LATENCY = "anomaly_latency"
    ANOMALY_ERROR_RATE = "anomaly_error_rate"
    ANOMALY_CPU = "anomaly_cpu"
    ANOMALY_MEMORY = "anomaly_memory"
    ANOMALY_QUEUE = "anomaly_queue"
    ANOMALY_DATABASE_LATENCY = "anomaly_database_latency"


class EventSeverity(StrEnum):
    """Deterministic severity classification."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventStatus(StrEnum):
    """Simple lifecycle for operational events."""

    ACTIVE = "active"
    CLEARED = "cleared"


class Event(BaseModel):
    """A normalized operational event derived from telemetry."""

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: EventType = Field(description="The type of the operational event")
    service_id: str = Field(description="The service this event pertains to")

    severity: EventSeverity = Field(description="Deterministic severity of the event")
    status: EventStatus = Field(default=EventStatus.ACTIVE, description="Current lifecycle state")
    message: str = Field(description="Human-readable description of the condition")

    # Correlation fields
    correlation_id: str | None = Field(
        default=None,
        description="Deterministic key used for deduplication (e.g., service_id + event_type)",
    )
    trace_id: str | None = Field(default=None, description="OTel trace ID if available")

    created_at: datetime = Field(description="When this condition was first observed")
    updated_at: datetime = Field(
        description="When this condition was last observed (for active events) or cleared"
    )

    # The actual observed metrics that triggered this event
    evidence: dict[str, float | int | str] = Field(
        default_factory=dict, description="Metrics backing this event"
    )
