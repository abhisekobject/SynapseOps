"""
SynapseOps Domain Models — Incident.

An Incident represents a significant degradation or failure in system behavior
that has been detected and requires investigation and potentially corrective action.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IncidentSeverity(StrEnum):
    """Severity classification for an incident.

    Severity reflects the potential impact on the system and users.
    It does not directly determine recovery authorization — that is the
    role of the risk model in the policy layer (Phase 9).
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    """Lifecycle status of an incident."""

    DETECTED = "detected"  # Anomaly detected; incident created
    INVESTIGATING = "investigating"  # Diagnosis in progress
    DIAGNOSED = "diagnosed"  # Root cause hypothesis available
    RECOVERING = "recovering"  # Recovery action in progress
    RESOLVED = "resolved"  # System verified as recovered
    ESCALATED = "escalated"  # Escalated to human operator
    CLOSED = "closed"  # Manually closed without automated resolution


class Incident(BaseModel):
    """Pydantic domain model representing a SynapseOps incident.

    An incident is created when correlated anomalies indicate a meaningful
    infrastructure problem. This model is the primary carrier of incident
    state through the operational loop.

    Note: This is a domain model for validation and transport.
          The corresponding ORM model lives in backend/models/db/incident.py.
          The action executor (Phase 10) operates separately from this model.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique incident identifier")
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Short human-readable summary of the incident",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of observed symptoms",
    )
    severity: IncidentSeverity = Field(
        ...,
        description="Estimated severity of the incident",
    )
    status: IncidentStatus = Field(
        default=IncidentStatus.DETECTED,
        description="Current lifecycle status",
    )
    affected_services: list[str] = Field(
        default_factory=list,
        description="Names of services exhibiting anomalous behavior",
    )
    probable_root_cause: str | None = Field(
        default=None,
        description="Best current hypothesis for the root cause (Phase 6+)",
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the incident was detected",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the incident was resolved (if applicable)",
    )

    model_config = {"from_attributes": True}
