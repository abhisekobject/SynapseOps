"""
SynapseOps Domain Models — Anomaly.

An Anomaly represents a detected deviation from expected or historically normal
behavior of a system metric, log pattern, or event sequence.

An anomaly is a signal — it may indicate an incident, a workload change, or
expected system evolution. Anomaly detection does not perform diagnosis.
The distinction between anomaly (signal) and incident (problem) is deliberate.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AnomalyType(StrEnum):
    """Classification of the anomaly signal type.

    These types correspond to the telemetry sources defined in the
    observability layer (Phase 3).
    """

    METRIC = "metric"  # Numerical metric deviation
    LOG_PATTERN = "log_pattern"  # Abnormal log pattern or error rate
    TRACE = "trace"  # Distributed trace anomaly (latency, errors)
    EVENT = "event"  # Unexpected discrete event


class AnomalySeverity(StrEnum):
    """Estimated severity of the anomaly signal."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnomalyStatus(StrEnum):
    """Processing status of the anomaly."""

    OPEN = "open"  # Detected; not yet associated with an incident
    CORRELATED = "correlated"  # Associated with an active incident
    RESOLVED = "resolved"  # Signal returned to normal range
    DISMISSED = "dismissed"  # Determined to be a false positive


class Anomaly(BaseModel):
    """Pydantic domain model representing a detected anomaly.

    Anomalies are the primary input to the incident creation pipeline.
    Multiple correlated anomalies may contribute to a single incident.

    Note: Confidence is a float in [0.0, 1.0] representing the detection
    model's certainty. Calibration of this value against empirical accuracy
    is part of the evaluation framework (Phase 5).
    """

    id: UUID = Field(default_factory=uuid4, description="Unique anomaly identifier")
    incident_id: UUID | None = Field(
        default=None,
        description="Associated incident ID (set when correlated)",
    )
    anomaly_type: AnomalyType = Field(..., description="Type of telemetry signal")
    severity: AnomalySeverity = Field(..., description="Estimated severity of the deviation")
    status: AnomalyStatus = Field(
        default=AnomalyStatus.OPEN,
        description="Current processing status",
    )
    service_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the service or component exhibiting the anomaly",
    )
    metric_name: str | None = Field(
        default=None,
        description="Name of the affected metric (for METRIC type anomalies)",
    )
    observed_value: float | None = Field(
        default=None,
        description="The observed metric value at detection time",
    )
    baseline_value: float | None = Field(
        default=None,
        description="The expected baseline value for comparison",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Detection confidence score in [0.0, 1.0]",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the detected deviation",
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of anomaly detection",
    )

    model_config = {"from_attributes": True}
