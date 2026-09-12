"""
SynapseOps Simulation — Domain Models.

Defines the Pydantic data models for the simulation layer:
- FailureType: the kind of failure being simulated
- FailureTarget: which simulated service/component is affected
- FailureScenario: a configured, active failure instance
- SimulationState: snapshot of all currently active failures
- API request/response contracts for failure injection

Design notes:
- All models are immutable (frozen=True where possible) except where
  the controller needs to update the `active` / `expired_at` fields.
- Severity is a float in [0.0, 1.0]. 0.0 means no effect; 1.0 is
  maximum effect (full crash, maximum latency, etc.).
- Duration of None means the failure persists until explicitly cleared.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FailureType(StrEnum):
    """The nature of the failure being simulated."""

    CRASH = "crash"
    """Service becomes completely unresponsive (HTTP 503 on all requests)."""

    LATENCY = "latency"
    """Service adds artificial delay to every request."""

    CPU_PRESSURE = "cpu_pressure"
    """Service simulates high CPU utilization, causing slow processing."""

    MEMORY_PRESSURE = "memory_pressure"
    """Service reports escalating memory usage in metrics."""

    DB_CONNECTION_EXHAUSTION = "db_connection_exhaustion"
    """Database connection pool is saturated; requests queue or fail."""

    ERROR_RATE_SPIKE = "error_rate_spike"
    """Service returns HTTP 500 for a percentage of requests."""

    NETWORK_PARTITION = "network_partition"
    """Service cannot reach its downstream dependencies (timeouts)."""

    DISK_IO_PRESSURE = "disk_io_pressure"
    """Service simulates slow disk I/O operations."""

    DOWNSTREAM_TIMEOUT = "downstream_timeout"
    """External downstream calls consistently time out."""

    CASCADE_SLOW = "cascade_slow"
    """Propagated slowness from a dependency (latency cascade)."""


class FailureTarget(StrEnum):
    """The simulated component affected by the failure."""

    GATEWAY = "gateway"
    """API gateway service."""

    API_SERVICE = "api_service"
    """Core API service."""

    WORKER = "worker"
    """Background worker service."""

    DATABASE = "database"
    """Simulated database (PostgreSQL effect)."""

    REDIS = "redis"
    """Simulated Redis cache."""

    ALL = "all"
    """Applies to all simulated services simultaneously."""


# ---------------------------------------------------------------------------
# Core scenario model
# ---------------------------------------------------------------------------


class FailureScenario(BaseModel):
    """A configured, active failure scenario.

    Created when a failure is injected and persisted in the controller's
    in-memory store. Published to Redis so simulated services can read it.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique scenario ID")
    name: str = Field(description="Human-readable scenario name")
    failure_type: FailureType = Field(description="The kind of failure being simulated")
    target: FailureTarget = Field(description="The affected component")
    severity: float = Field(
        description="Effect magnitude. 0.0 = no effect, 1.0 = maximum effect.",
        ge=0.0,
        le=1.0,
    )
    duration_seconds: float | None = Field(
        default=None,
        description="How long the failure lasts. None = persists until cleared.",
        gt=0,
    )
    description: str = Field(default="", description="Human-readable description of this scenario")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this scenario was activated",
    )
    active: bool = Field(default=True, description="Whether this scenario is currently active")

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return True if this scenario has exceeded its duration.

        Args:
            now: Current time (defaults to UTC now). Injected for testing.

        Returns:
            True if the scenario has a finite duration and has expired.
        """
        if not self.active:
            return True
        if self.duration_seconds is None:
            return False
        if now is None:
            now = datetime.now(UTC)
        elapsed = (now - self.started_at).total_seconds()
        return elapsed >= self.duration_seconds


# ---------------------------------------------------------------------------
# Simulation state snapshot
# ---------------------------------------------------------------------------


class SimulationState(BaseModel):
    """Snapshot of the simulation's current failure state.

    Returned by GET /api/v1/simulation/state.
    """

    active_scenarios: list[FailureScenario] = Field(
        default_factory=list,
        description="All currently active failure scenarios",
    )
    total_active: int = Field(
        default=0,
        description="Number of currently active scenarios",
    )
    snapshot_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this snapshot was taken",
    )

    @model_validator(mode="after")
    def _sync_total_active(self) -> SimulationState:
        """Keep total_active consistent with the active_scenarios list."""
        self.total_active = len([s for s in self.active_scenarios if s.active])
        return self

    def is_healthy(self) -> bool:
        """Return True if no failures are currently active."""
        return self.total_active == 0

    def active_for_target(self, target: FailureTarget) -> list[FailureScenario]:
        """Return active scenarios affecting a specific target (or ALL scenarios).

        Args:
            target: The component to filter by.

        Returns:
            List of active scenarios targeting this component or ALL.
        """
        return [
            s
            for s in self.active_scenarios
            if s.active and (s.target == target or s.target == FailureTarget.ALL)
        ]


# ---------------------------------------------------------------------------
# API request / response contracts
# ---------------------------------------------------------------------------


class InjectFailureRequest(BaseModel):
    """Request body for POST /api/v1/simulation/failures/inject.

    Either `scenario_name` (to activate a pre-defined scenario) OR
    the explicit failure parameters must be provided.
    """

    scenario_name: str | None = Field(
        default=None,
        description="Name of a pre-defined scenario to activate (see /scenarios endpoint).",
    )
    # Explicit failure parameters (used when scenario_name is None)
    name: str | None = Field(default=None, description="Custom scenario name")
    failure_type: FailureType | None = Field(default=None, description="Failure type")
    target: FailureTarget | None = Field(default=None, description="Affected target")
    severity: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Effect magnitude (0.0-1.0)",
    )
    duration_seconds: float | None = Field(
        default=300.0,
        description="Duration in seconds (None = permanent until cleared)",
        gt=0,
    )
    description: str = Field(default="", description="Human-readable description")

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("severity must be between 0.0 and 1.0")
        return v


class InjectFailureResponse(BaseModel):
    """Response body for POST /api/v1/simulation/failures/inject."""

    scenario: FailureScenario = Field(description="The newly activated scenario")
    message: str = Field(description="Human-readable confirmation message")


class ClearFailuresRequest(BaseModel):
    """Request body for DELETE /api/v1/simulation/failures."""

    target: FailureTarget | None = Field(
        default=None,
        description="Clear only failures for this target. None = clear all.",
    )


class ClearFailuresResponse(BaseModel):
    """Response body for DELETE /api/v1/simulation/failures."""

    cleared_count: int = Field(description="Number of scenarios cleared")
    message: str = Field(description="Human-readable confirmation message")


# ---------------------------------------------------------------------------
# Service health snapshot (emitted by each simulated service)
# ---------------------------------------------------------------------------


class ServiceHealthSnapshot(BaseModel):
    """Health and telemetry snapshot emitted by a simulated service.

    Each simulated service exposes a /health endpoint that returns this model.
    The SynapseOps backend polls these endpoints to aggregate system health.
    """

    service_name: str = Field(description="Identifier of this simulated service")
    status: str = Field(description="Overall service status: 'healthy', 'degraded', or 'crashed'")
    active_failure_types: list[str] = Field(
        default_factory=list,
        description="Names of failure types currently applied to this service",
    )
    # Telemetry fields (all services emit these; unused fields are None)
    requests_per_second: float | None = Field(default=None)
    error_rate_percent: float | None = Field(default=None)
    p50_latency_ms: float | None = Field(default=None)
    p99_latency_ms: float | None = Field(default=None)
    cpu_percent: float | None = Field(default=None)
    memory_mb: float | None = Field(default=None)
    active_connections: int | None = Field(default=None)
    queue_depth: int | None = Field(default=None)
    database_latency_ms: float | None = Field(default=None)
    snapshot_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
