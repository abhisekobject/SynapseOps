import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OutcomeState(StrEnum):
    """The verified state of the system after execution."""
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFIED_FAILURE = "VERIFIED_FAILURE"
    UNKNOWN = "UNKNOWN"
    PARTIAL = "PARTIAL"


class Observation(BaseModel):
    """A singular data point indicating system state after execution."""
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    plan_id: str
    plan_hash: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observation_source: str
    observed_state: str
    evidence_payload: dict = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="Quality/strength of evidence, NOT an override.")
    metadata: dict = Field(default_factory=dict)


class Evidence(BaseModel):
    """Structured record capturing the comparison of expected vs observed state."""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    observation_id: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expected_value: str
    observed_value: str
    comparison_matched: bool
    evidence_type: str = "DETERMINISTIC"


class OutcomeAssessment(BaseModel):
    """The final structured assessment of what actually happened."""
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    plan_id: str
    plan_hash: str

    execution_status: str
    outcome_status: OutcomeState

    expected_outcome: str
    observed_outcome: str

    evidence: list[Evidence] = Field(default_factory=list)

    assessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    is_simulated: bool = Field(default=False, description="True if the execution or observation was simulated.")
