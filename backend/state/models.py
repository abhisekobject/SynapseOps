from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceStatus(StrEnum):
    """Deterministic status of an infrastructure service."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ServiceState(BaseModel):
    """The aggregated current operational state of a service."""

    service_id: str = Field(description="Unique service identifier")
    status: ServiceStatus = Field(
        default=ServiceStatus.UNKNOWN, description="Current operational status"
    )

    # Selected recent telemetry for convenience
    latency_p99_ms: float | None = Field(default=None, description="Most recent p99 latency")
    error_rate_percent: float | None = Field(default=None, description="Most recent error rate")
    queue_depth: int | None = Field(default=None, description="Most recent queue depth")

    active_event_ids: list[str] = Field(
        default_factory=list, description="IDs of currently active operational events"
    )

    last_seen: datetime = Field(description="When the service last emitted telemetry")
    last_state_change: datetime = Field(description="When the service status last changed")


class SystemSnapshot(BaseModel):
    """A coherent snapshot of the entire infrastructure system state."""

    timestamp: datetime = Field(description="When this snapshot was generated")

    overall_status: ServiceStatus = Field(description="Worst-case status across all services")

    active_event_count: int = Field(description="Total number of active operational events")
    critical_event_count: int = Field(
        description="Total number of active CRITICAL operational events"
    )

    services: dict[str, ServiceState] = Field(description="Current state of all known services")
