import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from backend.intelligence.outcomes.models import OutcomeState


class FeedbackType(StrEnum):
    SUCCESS_CONFIRMATION = "SUCCESS_CONFIRMATION"
    FAILURE_SIGNAL = "FAILURE_SIGNAL"
    PARTIAL_SUCCESS_SIGNAL = "PARTIAL_SUCCESS_SIGNAL"
    UNKNOWN_SIGNAL = "UNKNOWN_SIGNAL"


class CausalAttribution(StrEnum):
    NONE = "NONE"
    OBSERVATIONAL = "OBSERVATIONAL"
    SUPPORTED = "SUPPORTED"
    UNKNOWN = "UNKNOWN"


class EvidenceCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class EvidenceConsistency(StrEnum):
    CONSISTENT = "CONSISTENT"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class FeedbackQuality(BaseModel):
    """Structured assessment of the quality of the feedback evidence."""
    evidence_completeness: EvidenceCompleteness
    evidence_consistency: EvidenceConsistency
    is_fresh: bool
    is_simulated: bool
    confidence: float = Field(ge=0.0, le=1.0)


class Feedback(BaseModel):
    """Answers what the outcome implies about the preceding decision."""
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    execution_id: str
    plan_id: str
    plan_hash: str
    outcome_state: OutcomeState
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    feedback_type: FeedbackType
    causal_attribution: CausalAttribution
    quality: FeedbackQuality
    metadata: dict = Field(default_factory=dict)


class SignalType(StrEnum):
    POSITIVE_EXPERIENCE = "POSITIVE_EXPERIENCE"
    NEGATIVE_EXPERIENCE = "NEGATIVE_EXPERIENCE"
    UNEXPECTED_RESULT = "UNEXPECTED_RESULT"
    UNKNOWN_INFORMATION = "UNKNOWN_INFORMATION"
    ENGINEERING_TEST_SIGNAL = "ENGINEERING_TEST_SIGNAL"


class LearningSignal(BaseModel):
    """Structured information that could be consumed by a future learning mechanism."""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    feedback_id: str
    signal_type: SignalType
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expected_result: str
    observed_result: str
    confidence: float
    is_simulated: bool


class DecisionState(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    DEFERRED = "DEFERRED"
    UNKNOWN = "UNKNOWN"


class LearningDecision(BaseModel):
    """Determines whether a LearningSignal is suitable for future learning."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    decision_state: DecisionState
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    explanation: str
