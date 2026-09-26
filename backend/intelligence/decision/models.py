"""
Phase 16 — Adaptive Decision Intelligence: Domain Models.

Defines Pydantic models for decision context, candidates, analysis, and status.

DESIGN RULES:
  - No field implies guaranteed outcome or causal proof.
  - Scores are labeled as "decision relevance scores", never "probability of success".
  - Environment isolation is explicit and encoded in the model.
  - Candidate actions come only from RecoveryActionType vocabulary.
  - All IDs are traceable to existing Phase 1-15 lineage identifiers.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from backend.intelligence.recovery.actions import ActionRiskLevel, RecoveryActionType

# ---------------------------------------------------------------------------
# Decision Status
# ---------------------------------------------------------------------------

class DecisionStatus(StrEnum):
    """
    Explicit bounded states for a DecisionAnalysis.

    These states do NOT duplicate or override the Safety/Authorization states
    from Phase 9. A decision reaching ELIGIBLE is merely a gate for referral
    to the existing Safety / Authorization pipeline.
    """
    ANALYZED = "ANALYZED"                  # Analysis complete, candidates evaluated
    NO_CANDIDATES = "NO_CANDIDATES"        # No candidate actions are eligible
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Not enough evidence to evaluate
    ERROR = "ERROR"                        # Decision analysis failed internally


class CandidateEligibility(StrEnum):
    """Whether a decision candidate is eligible for referral to Safety/Policy."""
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE_RISK = "INELIGIBLE_RISK"              # Risk level too high for automated referral
    INELIGIBLE_NO_EVIDENCE = "INELIGIBLE_NO_EVIDENCE"  # Zero supporting evidence
    INELIGIBLE_ENV_MISMATCH = "INELIGIBLE_ENV_MISMATCH"  # Simulation/real mismatch
    INELIGIBLE_RCA_MISMATCH = "INELIGIBLE_RCA_MISMATCH"  # Current RCA doesn't support this action


class EnvironmentContext(StrEnum):
    """The operational environment context for a decision."""
    SIMULATION = "SIMULATION"
    REAL = "REAL"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Decision Candidate
# ---------------------------------------------------------------------------

class HistoricalEvidenceSummary(BaseModel):
    """
    Summary of historical evidence supporting a decision candidate.

    IMPORTANT: All counts describe OBSERVATIONS — not causal proof.
    'observed_effectiveness' is a ratio of historical signal counts.
    It is NOT a probability of future success.
    """
    experience_count: int = Field(
        description="Number of relevant historical experiences found"
    )
    verified_experience_count: int = Field(
        description="Number of experiences with verified outcomes (Phase 11 verification)"
    )
    supporting_outcome_count: int = Field(
        description="Count of historically observed successful outcomes"
    )
    unsuccessful_outcome_count: int = Field(
        description="Count of historically observed unsuccessful outcomes"
    )
    partial_outcome_count: int = Field(
        description="Count of historically observed partial outcomes"
    )
    observed_effectiveness: float | None = Field(
        default=None,
        description=(
            "Historical ratio: supporting_outcome_count / experience_count. "
            "OBSERVATION ONLY — not a prediction or guarantee of future success."
        ),
    )
    environment_context: EnvironmentContext = Field(
        description="Environment from which historical evidence was drawn"
    )
    contributing_experience_ids: list[str] = Field(
        default_factory=list,
        description="IDs of source experiences contributing to this summary"
    )
    is_sufficient: bool = Field(
        description="Whether there is enough evidence to meaningfully support this candidate"
    )
    insufficiency_reason: str | None = Field(
        default=None,
        description="Explanation if is_sufficient=False"
    )


class DecisionCandidate(BaseModel):
    """
    A bounded decision candidate derived from current evidence + historical experience.

    BOUNDARIES:
      - action_type must come from RecoveryActionType vocabulary.
      - This object does NOT authorize or execute anything.
      - The 'score' is a decision relevance score, not a probability.
      - Eligibility refers to referral to Safety/Policy, not to guaranteed approval.
    """
    candidate_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this candidate evaluation"
    )
    action_type: RecoveryActionType = Field(
        description="The bounded action type from the SynapseOps recovery vocabulary"
    )
    target_component: str = Field(
        description="The infrastructure component this action would target"
    )
    risk_level: ActionRiskLevel = Field(
        description="Inherent risk level from the action registry (authoritative)"
    )
    is_reversible: bool = Field(
        description="Whether this action can be undone"
    )

    # Scoring (deterministic)
    decision_relevance_score: float = Field(
        description=(
            "A deterministic composite score [0.0, 1.0] reflecting how strongly "
            "current evidence and historical observations support this candidate. "
            "NOT a probability of success."
        )
    )
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Component scores contributing to decision_relevance_score"
    )

    # Historical evidence
    historical_evidence: HistoricalEvidenceSummary = Field(
        description="Summary of historical evidence supporting this candidate"
    )

    # Eligibility
    eligibility: CandidateEligibility = Field(
        description="Whether this candidate is eligible for referral to Safety/Policy"
    )
    eligibility_reasons: list[str] = Field(
        default_factory=list,
        description="Explanation of why this candidate is eligible or ineligible"
    )

    # Explanation
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Structured explanation of evidence supporting this candidate"
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Explicit caveats about uncertainty, evidence gaps, or conflicts"
    )

    # Verification
    verification_requirements: list[str] = Field(
        default_factory=list,
        description="Expected verification conditions if this action were executed"
    )

    # Lineage
    rca_alignment_services: list[str] = Field(
        default_factory=list,
        description="RCA candidate services that align with this action target"
    )


# ---------------------------------------------------------------------------
# Decision Context (input)
# ---------------------------------------------------------------------------

class DecisionContext(BaseModel):
    """
    Structured representation of the current operational context for decision analysis.

    All fields reference existing SynapseOps authoritative sources.
    No duplicate sources of truth are introduced.
    """
    # Incident identification
    incident_id: str | None = Field(
        default=None,
        description="Reference to a current incident (may be None for ad-hoc analysis)"
    )
    environment: EnvironmentContext = Field(
        default=EnvironmentContext.UNKNOWN,
        description="Current operational environment"
    )
    is_simulated: bool = Field(
        default=True,
        description="Whether this is a simulated or real incident"
    )

    # Current evidence from existing Phase systems
    affected_services: list[str] = Field(
        default_factory=list,
        description="Services currently identified as affected"
    )
    active_event_count: int = Field(
        default=0,
        description="Number of currently active events"
    )
    active_anomaly_services: list[str] = Field(
        default_factory=list,
        description="Services with active anomalies detected by Phase 4/5"
    )

    # RCA context (Phase 6)
    rca_top_candidates: list[str] = Field(
        default_factory=list,
        description="Top candidate services from RCA analysis (by score)"
    )
    rca_candidate_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Map of service_id to RCA score"
    )

    # Reasoning context (Phase 7)
    reasoning_recommended_actions: list[str] = Field(
        default_factory=list,
        description="Action types recommended by the AI incident reasoning (Phase 7)"
    )
    reasoning_summary: str | None = Field(
        default=None,
        description="Human-readable summary from Phase 7 reasoning"
    )

    # Configuration
    allow_simulation_evidence: bool = Field(
        default=False,
        description=(
            "If False (default), simulation historical evidence is excluded when "
            "environment is REAL. Must be explicitly set True to enable mixed mode. "
            "This is the primary safety guard for environment isolation."
        )
    )
    max_candidates: int = Field(
        default=5,
        description="Maximum number of candidates to evaluate"
    )
    min_evidence_threshold: int = Field(
        default=1,
        description="Minimum experience count to consider historical evidence sufficient"
    )


# ---------------------------------------------------------------------------
# Decision Analysis (output)
# ---------------------------------------------------------------------------

class DecisionAnalysis(BaseModel):
    """
    The complete output of a Phase 16 decision intelligence analysis.

    BOUNDARIES:
      - This object does NOT execute anything.
      - This object does NOT approve anything.
      - The top_candidate is a RECOMMENDATION for referral to Safety/Policy.
      - All evidence is clearly labeled as historical observation, not proof.
    """
    decision_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this decision analysis"
    )
    incident_id: str | None = Field(
        default=None,
        description="Incident this analysis was performed for"
    )
    environment: EnvironmentContext
    is_simulated: bool

    # Results
    status: DecisionStatus
    candidates: list[DecisionCandidate] = Field(
        default_factory=list,
        description="All evaluated candidates, ordered by decision_relevance_score descending"
    )
    top_candidate: DecisionCandidate | None = Field(
        default=None,
        description=(
            "The highest-scored eligible candidate. "
            "This is NOT a guaranteed recommendation — it is the most evidence-supported "
            "candidate for referral to the Safety/Policy pipeline."
        )
    )

    # Context summary
    context_summary: str = Field(
        description="Human-readable summary of the current decision context"
    )
    historical_evidence_available: bool = Field(
        description="Whether any relevant historical evidence was found"
    )
    historical_evidence_environment: EnvironmentContext | None = Field(
        default=None,
        description="Environment from which historical evidence was sourced"
    )

    # Caveats (mandatory)
    analysis_caveats: list[str] = Field(
        default_factory=list,
        description=(
            "Mandatory caveats about this analysis. Always present. "
            "Historical evidence is not causal proof. "
            "Scores are relevance indicators, not success probabilities."
        )
    )

    # Lineage
    rca_candidates_used: list[str] = Field(
        default_factory=list,
        description="RCA candidate services used in this analysis"
    )
    experience_ids_used: list[str] = Field(
        default_factory=list,
        description="Experience IDs that contributed historical evidence"
    )
    knowledge_ids_used: list[str] = Field(
        default_factory=list,
        description="Operational knowledge record IDs consulted"
    )

    # Metadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = Field(default="1.0")
    phase: str = Field(default="Phase 16 — Adaptive Decision Intelligence")

    # Error context
    error_message: str | None = Field(
        default=None,
        description="If status=ERROR, the reason for failure"
    )


# ---------------------------------------------------------------------------
# Deterministic ID generation
# ---------------------------------------------------------------------------

def generate_decision_id(
    incident_id: str | None,
    environment: str,
    is_simulated: bool,
    affected_services: list[str],
) -> str:
    """
    Generate a deterministic decision_id from stable input dimensions.

    This enables idempotent analysis: the same operational context
    always produces the same decision_id, preventing runaway duplicate records.
    """
    payload = json.dumps(
        {
            "affected_services": sorted(affected_services),
            "environment": environment,
            "incident_id": incident_id,
            "is_simulated": is_simulated,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]
