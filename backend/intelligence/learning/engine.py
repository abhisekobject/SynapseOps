"""
Phase 14 — Operational Learning: Learning Signal Engine.

Deterministically derives an ExperienceLearningSignal from a Phase 13 Experience.

Pipeline:
    Experience
        → Validation (structural + lineage)
        → Outcome Extraction (facts vs expectations vs observations)
        → Signal Type Classification (bounded vocabulary)
        → Signal Construction (immutable, traceable)

Rules:
    - One Experience → exactly one ExperienceLearningSignal
    - Same Experience always produces the same signal (deterministic)
    - Broken or untrusted experience lineage is rejected
    - No causal claims are produced
    - No system behavior is modified
"""

from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    ExperienceSignalType,
    SignalDerivationBasis,
    generate_signal_id,
)
from backend.intelligence.memory.models import Experience
from backend.intelligence.outcomes.models import OutcomeState

# States that are considered "verified success"
_VERIFIED_SUCCESS_STATES = frozenset({
    str(OutcomeState.VERIFIED_SUCCESS),
    "VERIFIED_SUCCESS",
})

# States indicating verification failed
_VERIFIED_FAILURE_STATES = frozenset({
    str(OutcomeState.VERIFIED_FAILURE),
    "VERIFIED_FAILURE",
})

_PARTIAL_STATES = frozenset({
    str(OutcomeState.PARTIAL),
    "PARTIAL",
})


class LearningEngine:
    """
    Deterministically derives ExperienceLearningSignals from Experiences.

    ARCHITECTURAL BOUNDARY:
    This engine ONLY reads from Experience records.
    It does NOT modify system behavior.
    It does NOT execute any infrastructure actions.
    It does NOT authorize any actions.
    It does NOT modify policies or permissions.
    """

    def generate_signal(self, experience: Experience) -> ExperienceLearningSignal:
        """
        Derive one ExperienceLearningSignal from one Experience.

        Args:
            experience: A Phase 13 Experience object with full lineage.

        Returns:
            An immutable ExperienceLearningSignal.

        Raises:
            ValueError: If the experience is structurally invalid or lineage is broken.
        """
        self._validate_experience(experience)

        signal_type = self._classify_signal_type(experience)
        derivation_basis = self._classify_derivation_basis(experience)

        # Deterministic signal_id: same experience + signal_type always yields the same ID
        signal_id = generate_signal_id(experience.experience_id, str(signal_type))

        return ExperienceLearningSignal(
            signal_id=signal_id,
            experience_id=experience.experience_id,
            incident_id=experience.incident_id,
            target_component=experience.target_component,
            action_type=str(experience.action_type),
            environment=experience.environment,
            is_simulated=experience.is_simulated,
            signal_type=signal_type,
            observed_outcome=experience.observed_outcome,
            expected_outcome=experience.expected_outcome,
            verification_status=str(experience.outcome_state),
            derivation_basis=derivation_basis,
            source_fingerprint=experience.fingerprint,
        )

    def generate_signals_bulk(self, experiences: list[Experience]) -> list[ExperienceLearningSignal]:
        """
        Generate signals from multiple experiences. Invalid experiences are
        collected as errors rather than stopping the entire batch.

        Returns:
            (signals, errors) tuple
        """
        signals = []
        errors = []
        for exp in experiences:
            try:
                signals.append(self.generate_signal(exp))
            except ValueError as e:
                errors.append({"experience_id": exp.experience_id, "error": str(e)})
        return signals, errors

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _validate_experience(self, experience: Experience) -> None:
        """
        Validate experience structural integrity and required lineage fields.
        Raises ValueError if the experience is not trustworthy.
        """
        # Required lineage IDs
        if not experience.experience_id:
            raise ValueError("Experience missing experience_id: lineage is broken")
        if not experience.execution_id:
            raise ValueError("Experience missing execution_id: lineage is broken")
        if not experience.assessment_id:
            raise ValueError("Experience missing assessment_id: lineage is broken")
        if not experience.feedback_id:
            raise ValueError("Experience missing feedback_id: lineage is broken")
        if not experience.learning_signal_id:
            raise ValueError("Experience missing learning_signal_id: lineage is broken")
        if not experience.plan_id:
            raise ValueError("Experience missing plan_id: lineage is broken")
        if not experience.plan_hash:
            raise ValueError("Experience missing plan_hash: lineage is broken")
        if not experience.fingerprint:
            raise ValueError("Experience missing fingerprint: integrity check failed")

        # Required semantic fields
        if not experience.target_component:
            raise ValueError("Experience missing target_component")
        if not experience.action_type:
            raise ValueError("Experience missing action_type")
        if not experience.outcome_state:
            raise ValueError("Experience missing outcome_state")
        if not experience.environment:
            raise ValueError("Experience missing environment: simulation/real isolation broken")

    def _classify_signal_type(self, experience: Experience) -> ExperienceSignalType:
        """
        Classify the signal type deterministically from outcome_state.
        Maps directly from what was observed — no causal inference.
        """
        outcome_state = str(experience.outcome_state)
        outcomes_match = experience.observed_outcome == experience.expected_outcome

        if outcome_state in _VERIFIED_SUCCESS_STATES:
            if outcomes_match:
                return ExperienceSignalType.ACTION_SUCCEEDED
            # Verified as success but outcomes don't match - still succeeded
            return ExperienceSignalType.EXPECTED_OUTCOME_MISMATCHED

        if outcome_state in _VERIFIED_FAILURE_STATES:
            return ExperienceSignalType.ACTION_FAILED

        if outcome_state in _PARTIAL_STATES:
            return ExperienceSignalType.ACTION_PARTIALLY_SUCCEEDED

        # Outcome_state does not correspond to a clear success/failure
        if outcomes_match:
            return ExperienceSignalType.EXPECTED_OUTCOME_MATCHED
        return ExperienceSignalType.EXPECTED_OUTCOME_MISMATCHED

    def _classify_derivation_basis(self, experience: Experience) -> SignalDerivationBasis:
        """Determine the derivation basis for this signal."""
        if experience.is_simulated:
            return SignalDerivationBasis.SIMULATION
        outcome_state = str(experience.outcome_state)
        if outcome_state in _VERIFIED_SUCCESS_STATES | _VERIFIED_FAILURE_STATES:
            return SignalDerivationBasis.VERIFIED_EXPERIENCE
        return SignalDerivationBasis.UNVERIFIED_EXPERIENCE
