"""
Phase 16 — Adaptive Decision Intelligence: Historical Experience Retrieval.

Retrieves and classifies historical experiences and learning signals
relevant to the current decision context.

DESIGN RULES:
  - Reuses Phase 13 Experience objects and Phase 14 learning signals.
  - Does NOT create a second memory system.
  - Simulation/real isolation is the primary safety guard.
  - All retrieval is deterministic (same input → same output).
  - Evidence is classified as OBSERVATION, never as causal proof.
"""

from __future__ import annotations

from backend.intelligence.decision.models import (
    EnvironmentContext,
    HistoricalEvidenceSummary,
)
from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    ExperienceSignalType,
    OperationalKnowledge,
)
from backend.intelligence.memory.models import Experience
from backend.intelligence.recovery.actions import RecoveryActionType

# The minimum "verified outcome" signal types (Phase 11 verification succeeded)
_VERIFIED_SUCCESS_SIGNALS = frozenset({
    ExperienceSignalType.ACTION_SUCCEEDED,
    ExperienceSignalType.RECOVERY_EFFECTIVE,
    ExperienceSignalType.EXPECTED_OUTCOME_MATCHED,
})

_UNSUCCESSFUL_SIGNALS = frozenset({
    ExperienceSignalType.ACTION_FAILED,
    ExperienceSignalType.RECOVERY_INEFFECTIVE,
    ExperienceSignalType.EXPECTED_OUTCOME_MISMATCHED,
})

_PARTIAL_SIGNALS = frozenset({
    ExperienceSignalType.ACTION_PARTIALLY_SUCCEEDED,
})

# Evidence is considered "sufficient" when at least this many experiences exist
_MIN_MEANINGFUL_EVIDENCE = 1


class DecisionRetrieval:
    """
    Retrieves relevant historical evidence for a given action type and target.

    ARCHITECTURAL BOUNDARY:
      This class only reads existing Experience and LearningSignal records.
      It does NOT write, modify, or create any new records.
      It does NOT execute actions.
      It does NOT authorize actions.
    """

    def retrieve_evidence(
        self,
        *,
        action_type: RecoveryActionType,
        target_component: str,
        current_is_simulated: bool,
        allow_simulation_evidence: bool,
        experiences: list[Experience],
        learning_signals: list[ExperienceLearningSignal],
        operational_knowledge: list[OperationalKnowledge],
        min_evidence_threshold: int = _MIN_MEANINGFUL_EVIDENCE,
    ) -> HistoricalEvidenceSummary:
        """
        Retrieve and summarize historical evidence for the given action/target combination.

        Environment Isolation Policy (mandatory):
          - REAL incident + allow_simulation_evidence=False → only REAL experiences
          - REAL incident + allow_simulation_evidence=True  → MIXED (labeled explicitly)
          - SIMULATION incident → only SIMULATION experiences

        Args:
            action_type: The recovery action being evaluated.
            target_component: The service this action would target.
            current_is_simulated: Whether the current incident is simulated.
            allow_simulation_evidence: Only True if caller explicitly opted in to mixed mode.
            experiences: All available Phase 13 experiences.
            learning_signals: All available Phase 14 learning signals.
            operational_knowledge: All available Phase 14 operational knowledge records.
            min_evidence_threshold: Minimum experiences to consider evidence sufficient.

        Returns:
            A HistoricalEvidenceSummary with honest representation of evidence.
        """
        # Step 1: Filter experiences by action_type and target_component
        candidate_experiences = self._filter_experiences(
            experiences=experiences,
            action_type=action_type,
            target_component=target_component,
        )

        # Step 2: Apply environment isolation
        filtered_experiences, env_context = self._apply_env_isolation(
            experiences=candidate_experiences,
            current_is_simulated=current_is_simulated,
            allow_simulation_evidence=allow_simulation_evidence,
        )

        # Step 3: Gather learning signals for these experiences
        experience_ids = {e.experience_id for e in filtered_experiences}
        relevant_signals = [
            s for s in learning_signals if s.experience_id in experience_ids
        ]

        # Step 4: Count outcomes from signals
        supporting = 0
        unsuccessful = 0
        partial = 0
        verified_count = 0

        for sig in relevant_signals:
            sig_type = ExperienceSignalType(sig.signal_type)
            if sig_type in _VERIFIED_SUCCESS_SIGNALS:
                supporting += 1
                verified_count += 1
            elif sig_type in _UNSUCCESSFUL_SIGNALS:
                unsuccessful += 1
                verified_count += 1
            elif sig_type in _PARTIAL_SIGNALS:
                partial += 1

        total = len(filtered_experiences)

        # Step 5: Check operational knowledge for pre-aggregated stats
        # (supplements the raw experience counts if available)
        ok_record = self._find_operational_knowledge(
            knowledge=operational_knowledge,
            action_type=action_type,
            target_component=target_component,
            is_simulated=current_is_simulated,
        )
        if ok_record and ok_record.supporting_experience_count > total:
            # Use aggregated knowledge if it has more evidence
            total = ok_record.supporting_experience_count
            supporting = ok_record.successful_count
            unsuccessful = ok_record.failed_count
            partial = ok_record.partial_count
            verified_count = ok_record.verification_success_count

        # Step 6: Compute effectiveness ratio
        effectiveness: float | None = None
        if total > 0:
            effectiveness = round(supporting / total, 6)

        # Step 7: Determine sufficiency
        is_sufficient = total >= min_evidence_threshold
        insufficiency_reason: str | None = None
        if not is_sufficient:
            if total == 0:
                insufficiency_reason = (
                    f"No historical experiences found for action '{action_type}' "
                    f"on target '{target_component}'"
                )
            else:
                insufficiency_reason = (
                    f"Only {total} experience(s) found; "
                    f"minimum required: {min_evidence_threshold}"
                )

        return HistoricalEvidenceSummary(
            experience_count=total,
            verified_experience_count=verified_count,
            supporting_outcome_count=supporting,
            unsuccessful_outcome_count=unsuccessful,
            partial_outcome_count=partial,
            observed_effectiveness=effectiveness,
            environment_context=env_context,
            contributing_experience_ids=sorted(
                e.experience_id for e in filtered_experiences
            ),
            is_sufficient=is_sufficient,
            insufficiency_reason=insufficiency_reason,
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _filter_experiences(
        self,
        *,
        experiences: list[Experience],
        action_type: RecoveryActionType,
        target_component: str,
    ) -> list[Experience]:
        """Filter experiences to those matching action_type and target_component."""
        action_str = str(action_type)
        return [
            e for e in experiences
            if str(e.action_type) == action_str
            and e.target_component == target_component
        ]

    def _apply_env_isolation(
        self,
        *,
        experiences: list[Experience],
        current_is_simulated: bool,
        allow_simulation_evidence: bool,
    ) -> tuple[list[Experience], EnvironmentContext]:
        """
        Apply the environment isolation policy.

        Returns:
            (filtered_experiences, environment_context_label)
        """
        if current_is_simulated:
            # Simulation incident → simulation evidence only
            filtered = [e for e in experiences if e.is_simulated]
            return filtered, EnvironmentContext.SIMULATION

        # Real incident path
        if not allow_simulation_evidence:
            # Default: exclude simulation evidence
            filtered = [e for e in experiences if not e.is_simulated]
            return filtered, EnvironmentContext.REAL

        # Explicitly opted in to mixed mode
        # Label it MIXED so callers cannot misrepresent this as pure real evidence
        return experiences, EnvironmentContext.MIXED

    def _find_operational_knowledge(
        self,
        *,
        knowledge: list[OperationalKnowledge],
        action_type: RecoveryActionType,
        target_component: str,
        is_simulated: bool,
    ) -> OperationalKnowledge | None:
        """
        Find the most specific OperationalKnowledge record for the given dimensions.
        Returns None if not found.
        """
        action_str = str(action_type)
        for ok in knowledge:
            if (
                ok.action_type == action_str
                and ok.target_component == target_component
                and ok.is_simulated == is_simulated
            ):
                return ok
        return None
