"""
Phase 14 — Operational Learning: Knowledge Aggregator.

Deterministically aggregates ExperienceLearningSignals into OperationalKnowledge.

Aggregation Formula:
    observed_effectiveness = successful_count / supporting_experience_count
    (only when supporting_experience_count > 0)

Rules:
    - Aggregation is purely deterministic: same signals → same knowledge
    - Simulation and production environments are NEVER mixed accidentally
    - Requesting mixed aggregation requires explicit opt-in
    - No causal claims are produced
    - No system behavior is modified
    - All results are reproducible from source signals

Environment Isolation Policy:
    By default, is_simulated=True experiences can never affect
    is_simulated=False aggregates (and vice versa).
    Mixed analysis is only allowed when the caller explicitly requests it
    by passing is_simulated=None in the query, and the result is labeled
    as a mixed aggregate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    ExperienceSignalType,
    KnowledgeAggregationQuery,
    OperationalKnowledge,
    generate_knowledge_id,
)


class KnowledgeAggregator:
    """
    Aggregates ExperienceLearningSignals into OperationalKnowledge.

    ARCHITECTURAL BOUNDARY:
    This aggregator ONLY reads from signal records.
    It does NOT modify system behavior.
    It does NOT execute any infrastructure actions.
    It does NOT authorize any actions.
    It does NOT produce causal conclusions.
    """

    def aggregate(
        self,
        signals: list[ExperienceLearningSignal],
        query: KnowledgeAggregationQuery,
    ) -> OperationalKnowledge:
        """
        Deterministically aggregate signals matching the query dimensions.

        Environment Isolation:
            If query.is_simulated is True → only simulated signals
            If query.is_simulated is False → only production signals
            If query.is_simulated is None → all signals (mixed, labeled)

        Args:
            signals: Pool of ExperienceLearningSignals to aggregate over.
            query: Specifies filtering dimensions.

        Returns:
            An OperationalKnowledge aggregate (reproducible from same inputs).
        """
        # Filter signals to those matching the query
        matching = self._filter_signals(signals, query)

        # Deterministic knowledge_id based on aggregation dimensions only
        knowledge_id = generate_knowledge_id(
            target_component=query.target_component,
            action_type=query.action_type,
            environment=query.environment,
            is_simulated=query.is_simulated,
        )

        if not matching:
            return OperationalKnowledge(
                knowledge_id=knowledge_id,
                target_component=query.target_component,
                action_type=query.action_type,
                environment=query.environment,
                is_simulated=query.is_simulated,
                supporting_experience_count=0,
                observed_effectiveness=None,
            )

        # Collect evidence
        successful = 0
        failed = 0
        partial = 0
        verification_success = 0
        verification_failure = 0
        outcome_match = 0
        outcome_mismatch = 0
        source_fps: list[str] = []
        signal_ids: list[str] = []
        experience_ids: list[str] = []
        timestamps: list[datetime] = []

        for sig in matching:
            signal_ids.append(sig.signal_id)
            experience_ids.append(sig.experience_id)
            source_fps.append(sig.source_fingerprint)
            timestamps.append(sig.created_at)

            stype = sig.signal_type
            if stype == ExperienceSignalType.ACTION_SUCCEEDED:
                successful += 1
                verification_success += 1
                outcome_match += 1
            elif stype == ExperienceSignalType.ACTION_FAILED:
                failed += 1
                verification_failure += 1
            elif stype == ExperienceSignalType.ACTION_PARTIALLY_SUCCEEDED:
                partial += 1
            elif stype == ExperienceSignalType.VERIFICATION_SUCCEEDED:
                verification_success += 1
            elif stype == ExperienceSignalType.VERIFICATION_FAILED:
                verification_failure += 1
            elif stype == ExperienceSignalType.EXPECTED_OUTCOME_MATCHED:
                outcome_match += 1
                verification_success += 1
            elif stype == ExperienceSignalType.EXPECTED_OUTCOME_MISMATCHED:
                outcome_mismatch += 1
            elif stype == ExperienceSignalType.RECOVERY_EFFECTIVE:
                successful += 1
            elif stype == ExperienceSignalType.RECOVERY_INEFFECTIVE:
                failed += 1

        total = len(matching)

        # Deterministic effectiveness formula:
        # successful_count / supporting_experience_count
        # OBSERVATION: not a prediction or causal claim
        effectiveness: float | None = None
        if total > 0:
            effectiveness = round(successful / total, 6)

        # Deduplicate source fingerprints (maintain insertion order for determinism)
        seen: set[str] = set()
        unique_fps = []
        for fp in source_fps:
            if fp not in seen:
                seen.add(fp)
                unique_fps.append(fp)

        first_observed = min(timestamps) if timestamps else None
        last_observed = max(timestamps) if timestamps else None

        return OperationalKnowledge(
            knowledge_id=knowledge_id,
            target_component=query.target_component,
            action_type=query.action_type,
            environment=query.environment,
            is_simulated=query.is_simulated,
            supporting_experience_count=total,
            successful_count=successful,
            failed_count=failed,
            partial_count=partial,
            verification_success_count=verification_success,
            verification_failure_count=verification_failure,
            outcome_match_count=outcome_match,
            outcome_mismatch_count=outcome_mismatch,
            observed_effectiveness=effectiveness,
            source_fingerprints=unique_fps,
            contributing_signal_ids=sorted(signal_ids),
            contributing_experience_ids=sorted(experience_ids),
            first_observed_at=first_observed,
            last_observed_at=last_observed,
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _filter_signals(
        self,
        signals: list[ExperienceLearningSignal],
        query: KnowledgeAggregationQuery,
    ) -> list[ExperienceLearningSignal]:
        """
        Filter signals by query dimensions.
        Signals are sorted by created_at then signal_id for deterministic ordering.
        """
        result = []
        for sig in signals:
            if query.target_component is not None and sig.target_component != query.target_component:
                continue
            if query.action_type is not None and sig.action_type != query.action_type:
                continue
            if query.environment is not None and sig.environment != query.environment:
                continue
            if query.incident_id is not None and sig.incident_id != query.incident_id:
                continue
            # Environment isolation: is_simulated filter
            # None means "all" (explicit mixed mode — labeled in knowledge_id)
            if query.is_simulated is not None and sig.is_simulated != query.is_simulated:
                continue
            result.append(sig)

        # Deterministic sort: created_at ASC, then signal_id ASC for ties
        result.sort(key=lambda s: (s.created_at, s.signal_id))
        return result
