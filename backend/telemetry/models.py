from datetime import datetime

from pydantic import BaseModel, Field


class TelemetrySnapshot(BaseModel):
    """Normalized representation of a service's raw telemetry at a given time."""

    service_id: str = Field(description="Unique identifier of the observed service")
    timestamp: datetime = Field(description="UTC timestamp of the observation")

    # Telemetry metrics - Nullable to handle different service profiles
    requests_per_second: float | None = None
    error_rate_percent: float | None = None
    p50_latency_ms: float | None = None
    p99_latency_ms: float | None = None

    cpu_percent: float | None = None
    memory_mb: float | None = None
    queue_depth: int | None = None

    # Fundamental indicators
    is_healthy: bool = Field(description="Whether the service reports as fully healthy")
    active_failure_count: int = Field(
        default=0, description="Number of failure scenarios currently active"
    )
