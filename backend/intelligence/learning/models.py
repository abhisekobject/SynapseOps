"""
Phase 14 — Operational Learning: Domain Models.

Defines the bounded vocabulary and structures for experience-derived
learning signals and aggregated operational knowledge.

Design Philosophy:
- ExperienceLearningSignal: one-to-one mapping from an Experience. Immutable.
- OperationalKnowledge: deterministic aggregate over many signals. Reproducible.
- No causal claims. All fields describe OBSERVATIONS, not causes.
- Simulation and production environments are strictly separated.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ExperienceSignalType(StrEnum):
    """Bounded vocabulary of learning signal types.

    Each type describes an observed historical outcome.
    None of these types encode causality.
    """
    ACTION_SUCCEEDED = "ACTION_SUCCEEDED"
    ACTION_FAILED = "ACTION_FAILED"
    ACTION_PARTIALLY_SUCCEEDED = "ACTION_PARTIALLY_SUCCEEDED"
    EXPECTED_OUTCOME_MATCHED = "EXPECTED_OUTCOME_MATCHED"
    EXPECTED_OUTCOME_MISMATCHED = "EXPECTED_OUTCOME_MISMATCHED"
    VERIFICATION_SUCCEEDED = "VERIFICATION_SUCCEEDED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    RECOVERY_EFFECTIVE = "RECOVERY_EFFECTIVE"
    RECOVERY_INEFFECTIVE = "RECOVERY_INEFFECTIVE"
    INCIDENT_RECURRED = "INCIDENT_RECURRED"


class SignalDerivationBasis(StrEnum):
    """The basis from which a signal was derived."""
    VERIFIED_EXPERIENCE = "VERIFIED_EXPERIENCE"
    UNVERIFIED_EXPERIENCE = "UNVERIFIED_EXPERIENCE"
    SIMULATION = "SIMULATION"


class ExperienceLearningSignal(BaseModel):
    """
    A structured, immutable learning signal derived from a single Experience.

    BOUNDARY: This is DERIVED EVIDENCE, not raw fact.
    It represents what was OBSERVED — not what was CAUSED.

    Fields:
        signal_id: Unique identifier. Deterministic from source_fingerprint.
        experience_id: Source Experience this was derived from.
        incident_id: Optional reference to the originating incident.
        target_component: The infrastructure component the action targeted.
        action_type: The recovery action type that was taken.
        environment: The environment in which this experience occurred.
        is_simulated: True if this came from simulated infrastructure.
        signal_type: Bounded classification of the observed outcome.
        observed_outcome: What was empirically observed.
        expected_outcome: What was originally expected.
        verification_status: The outcome state from Phase 11 verification.
        derivation_basis: Whether this came from a verified experience.
        source_fingerprint: Deterministic hash of the source experience.
        schema_version: Version for forward compatibility.
        created_at: Timestamp of signal generation.
    """
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experience_id: str
    incident_id: str | None = None
    target_component: str
    action_type: str
    environment: str
    is_simulated: bool
    signal_type: ExperienceSignalType
    observed_outcome: str
    expected_outcome: str
    verification_status: str
    derivation_basis: SignalDerivationBasis
    source_fingerprint: str
    schema_version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeAggregationQuery(BaseModel):
    """Specifies dimensions for knowledge aggregation."""
    target_component: str | None = None
    action_type: str | None = None
    environment: str | None = None
    is_simulated: bool | None = None
    incident_id: str | None = None


class OperationalKnowledge(BaseModel):
    """
    Deterministic aggregate of ExperienceLearningSignals.

    BOUNDARY: Contains HISTORICAL EVIDENCE ONLY.
    Does NOT authorize, execute, or trigger behavioral change.
    Does NOT claim causality.
    Does NOT contain predictions.

    All counts are reproducible from source signals.
    observed_effectiveness = successful_count / eligible_experience_count
    (only defined when eligible_experience_count > 0)
    """
    knowledge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # Aggregation dimensions
    target_component: str | None = None
    action_type: str | None = None
    environment: str | None = None
    is_simulated: bool | None = None

    # Evidence counts
    supporting_experience_count: int = 0
    successful_count: int = 0
    failed_count: int = 0
    partial_count: int = 0
    verification_success_count: int = 0
    verification_failure_count: int = 0
    outcome_match_count: int = 0
    outcome_mismatch_count: int = 0

    # Derived statistic — OBSERVATION ONLY, not prediction
    # Formula: successful_count / supporting_experience_count
    observed_effectiveness: float | None = None

    # Evidence support
    source_fingerprints: list[str] = Field(default_factory=list)
    contributing_signal_ids: list[str] = Field(default_factory=list)
    contributing_experience_ids: list[str] = Field(default_factory=list)

    # Temporal
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = Field(default="1.0")


def generate_signal_id(experience_id: str, signal_type: str) -> str:
    """
    Generate a deterministic signal_id from (experience_id, signal_type).
    Ensures idempotency: same inputs always produce the same signal_id.
    """
    payload = json.dumps({"experience_id": experience_id, "signal_type": signal_type}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def generate_knowledge_id(
    target_component: str | None,
    action_type: str | None,
    environment: str | None,
    is_simulated: bool | None,
) -> str:
    """
    Generate a deterministic knowledge_id from aggregation dimensions.
    Ensures that repeated aggregation over same dimensions yields the same ID.
    """
    payload = json.dumps({
        "action_type": action_type,
        "environment": environment,
        "is_simulated": is_simulated,
        "target_component": target_component,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
