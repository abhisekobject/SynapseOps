import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.intelligence.feedback.models import FeedbackType, SignalType
from backend.intelligence.outcomes.models import OutcomeState
from backend.intelligence.recovery.actions import RecoveryActionType


class Experience(BaseModel):
    """An episodic memory recording a historical interaction episode."""
    experience_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Lineage IDs
    incident_id: str | None = None
    learning_signal_id: str
    feedback_id: str
    assessment_id: str
    execution_id: str
    plan_id: str
    plan_hash: str

    # Facts: What context the action was taken in
    target_component: str
    action_type: str | RecoveryActionType

    # Expectations: What was expected
    expected_outcome: str

    # Observations: What was actually observed
    observed_outcome: str

    # Assessment: What verification concluded
    outcome_state: str | OutcomeState
    feedback_type: str | FeedbackType
    learning_signal_type: str | SignalType

    # Boundaries
    is_simulated: bool
    environment: str = Field(description="E.g., SIMULATED, PRODUCTION")
    fingerprint: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(default="Phase12_Artifacts")
    metadata: dict = Field(default_factory=dict)


class RetrievalQuery(BaseModel):
    """A structured query for retrieving historical experiences."""
    incident_id: str | None = None
    target_component: str | None = None
    action_type: str | RecoveryActionType | None = None
    expected_outcome: str | None = None
    observed_outcome: str | None = None
    outcome_state: str | OutcomeState | None = None
    feedback_type: str | FeedbackType | None = None
    learning_signal_type: str | SignalType | None = None
    is_simulated: bool | None = None
    environment: str | None = None


class RelevanceScore(BaseModel):
    """Deterministic score with explainable reasons."""
    score: int
    reasons: list[str] = Field(default_factory=list)


class RetrievedExperience(BaseModel):
    """Wrapper for a retrieved experience and its relevance score."""
    experience: Experience
    relevance: RelevanceScore


class RetrievalResult(BaseModel):
    """The result of a deterministic retrieval query."""
    retrieval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: RetrievalQuery
    results: list[RetrievedExperience] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_simulated: bool = Field(default=False)
