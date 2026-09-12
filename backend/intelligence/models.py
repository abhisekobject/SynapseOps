import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RCAEvidence(BaseModel):
    """A single piece of evidence supporting a root-cause candidate."""

    type: str = Field(description="Type of evidence (e.g., temporal_precedence, downstream_impact)")
    description: str = Field(description="Human-readable explanation of the evidence")
    weight: float = Field(description="Points contributed to the candidate's score")


class RCACandidate(BaseModel):
    """A service identified as a candidate root cause."""

    component: str = Field(description="Service identifier")
    score: float = Field(description="Root cause score (0.0 to 1.0)")
    evidence: list[RCAEvidence] = Field(default_factory=list, description="List of supporting evidence")
    affected_components: list[str] = Field(
        default_factory=list, description="Downstream components suspected to be affected by this candidate"
    )
    confidence: str = Field(description="Confidence category (e.g., HIGH, MEDIUM, LOW)")


class RCAResult(BaseModel):
    """Complete snapshot of a Root Cause Analysis evaluation."""

    analysis_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique analysis identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When analysis occurred")
    window_minutes: int = Field(description="Time window used for correlating events")
    candidates: list[RCACandidate] = Field(
        default_factory=list, description="Ranked list of root-cause candidates"
    )
