"""
Phase 16 — Adaptive Decision Intelligence: Decision Engine.

The main orchestrator that:
  1. Accepts a DecisionContext (current incident evidence)
  2. Retrieves relevant historical experiences (Phase 13)
  3. Retrieves learning signals (Phase 14)
  4. Retrieves operational knowledge (Phase 14)
  5. Scores each bounded candidate action deterministically
  6. Returns a DecisionAnalysis with explainable, honest candidates

CRITICAL SAFETY BOUNDARIES (enforced architecturally):
  - The engine NEVER calls any execution function.
  - The engine NEVER calls any Safety/Policy function.
  - The engine NEVER modifies any Experience, Signal, or Knowledge record.
  - The engine NEVER generates shell commands or arbitrary strings as actions.
  - Candidate actions come ONLY from RecoveryActionType vocabulary.
  - Simulation/real isolation is enforced in DecisionRetrieval.
"""

from __future__ import annotations

import structlog

from backend.intelligence.decision.models import (
    DecisionAnalysis,
    DecisionCandidate,
    DecisionContext,
    DecisionStatus,
    EnvironmentContext,
    generate_decision_id,
)
from backend.intelligence.decision.retrieval import DecisionRetrieval
from backend.intelligence.decision.scoring import DecisionScorer
from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    OperationalKnowledge,
)
from backend.intelligence.memory.models import Experience
from backend.intelligence.recovery.actions import (
    RecoveryActionType,
)

log = structlog.get_logger(__name__)

# Maximum number of candidate (action_type, target) pairs to evaluate
_MAX_CANDIDATE_PAIRS = 20


class DecisionEngine:
    """
    Phase 16 Adaptive Decision Intelligence engine.

    ARCHITECTURAL POSITION:
        Sits between Phase 7 (AI Reasoning) / Phase 8 (Recovery Planning)
        and Phase 9 (Safety/Policy). Provides evidence-enriched candidate
        evaluation but does NOT replace or bypass Safety.

    INPUT: DecisionContext + historical evidence stores
    OUTPUT: DecisionAnalysis with ranked, explainable candidates

    BOUNDARY:
        This class is a pure analysis engine.
        It has no side effects on any other system component.
    """

    def __init__(self) -> None:
        self._retrieval = DecisionRetrieval()
        self._scorer = DecisionScorer()

    def analyze(
        self,
        *,
        context: DecisionContext,
        experiences: list[Experience],
        learning_signals: list[ExperienceLearningSignal],
        operational_knowledge: list[OperationalKnowledge],
    ) -> DecisionAnalysis:
        """
        Perform a complete decision intelligence analysis.

        Args:
            context: Current operational decision context.
            experiences: All available Phase 13 episodic experiences.
            learning_signals: All available Phase 14 learning signals.
            operational_knowledge: All available Phase 14 knowledge records.

        Returns:
            A DecisionAnalysis with ranked, explainable, evidence-backed candidates.

        Notes:
            - Never raises; returns DecisionAnalysis with status=ERROR on failure.
            - Deterministic: same inputs → same analysis.
        """
        log.info(
            "decision_analysis_started",
            incident_id=context.incident_id,
            environment=context.environment,
            affected_services=context.affected_services,
            rca_candidates=context.rca_top_candidates,
        )

        try:
            return self._run_analysis(
                context=context,
                experiences=experiences,
                learning_signals=learning_signals,
                operational_knowledge=operational_knowledge,
            )
        except Exception as exc:
            log.error("decision_analysis_failed", error=str(exc), exc_info=True)
            return DecisionAnalysis(
                decision_id=generate_decision_id(
                    incident_id=context.incident_id,
                    environment=str(context.environment),
                    is_simulated=context.is_simulated,
                    affected_services=context.affected_services,
                ),
                incident_id=context.incident_id,
                environment=context.environment,
                is_simulated=context.is_simulated,
                status=DecisionStatus.ERROR,
                context_summary="Decision analysis failed due to an internal error.",
                historical_evidence_available=False,
                analysis_caveats=[
                    "Decision analysis encountered an internal error. "
                    "The system remains safe — no actions were taken.",
                    "Historical evidence is not causal proof.",
                ],
                error_message=str(exc),
            )

    def _run_analysis(
        self,
        *,
        context: DecisionContext,
        experiences: list[Experience],
        learning_signals: list[ExperienceLearningSignal],
        operational_knowledge: list[OperationalKnowledge],
    ) -> DecisionAnalysis:
        """Inner implementation; exceptions propagate to analyze()."""

        # Step 1: Determine candidate (action_type, target) pairs from context
        candidate_pairs = self._enumerate_candidate_pairs(context)

        if not candidate_pairs:
            return DecisionAnalysis(
                decision_id=generate_decision_id(
                    incident_id=context.incident_id,
                    environment=str(context.environment),
                    is_simulated=context.is_simulated,
                    affected_services=context.affected_services,
                ),
                incident_id=context.incident_id,
                environment=context.environment,
                is_simulated=context.is_simulated,
                status=DecisionStatus.NO_CANDIDATES,
                context_summary=self._build_context_summary(context),
                historical_evidence_available=False,
                analysis_caveats=[
                    "No candidate action/target pairs could be identified from current evidence.",
                    "Historical evidence is not causal proof.",
                    "Decision relevance scores are not probabilities.",
                ],
            )

        # Step 2: Score each candidate pair
        all_experience_ids: list[str] = []
        all_candidates: list[DecisionCandidate] = []

        for action_type, target_component in candidate_pairs[:_MAX_CANDIDATE_PAIRS]:
            # Retrieve historical evidence for this specific (action, target)
            evidence = self._retrieval.retrieve_evidence(
                action_type=action_type,
                target_component=target_component,
                current_is_simulated=context.is_simulated,
                allow_simulation_evidence=context.allow_simulation_evidence,
                experiences=experiences,
                learning_signals=learning_signals,
                operational_knowledge=operational_knowledge,
                min_evidence_threshold=context.min_evidence_threshold,
            )
            all_experience_ids.extend(evidence.contributing_experience_ids)

            # Build scored candidate
            candidate = self._scorer.build_candidate(
                action_type=action_type,
                target_component=target_component,
                rca_candidates=context.rca_top_candidates,
                rca_scores=context.rca_candidate_scores,
                reasoning_recommended=context.reasoning_recommended_actions,
                historical_evidence=evidence,
                current_environment=context.environment,
                allow_simulation_evidence=context.allow_simulation_evidence,
            )
            all_candidates.append(candidate)

        # Step 3: Sort candidates deterministically
        # Primary: score descending
        # Secondary: action_type ascending (lexicographic — deterministic tie-break)
        # Tertiary: target_component ascending
        all_candidates.sort(
            key=lambda c: (
                -c.decision_relevance_score,
                str(c.action_type),
                c.target_component,
            )
        )

        # Limit to max_candidates
        all_candidates = all_candidates[: context.max_candidates]

        # Step 4: Identify eligible candidates
        eligible = [c for c in all_candidates if c.eligibility.startswith("ELIGIBLE")]

        # Step 5: Determine top candidate (most relevant eligible candidate)
        top_candidate = eligible[0] if eligible else None

        # Step 6: Determine overall status
        if not eligible:
            status = DecisionStatus.NO_CANDIDATES
        elif all(
            not c.historical_evidence.is_sufficient for c in all_candidates
        ):
            status = DecisionStatus.INSUFFICIENT_EVIDENCE
        else:
            status = DecisionStatus.ANALYZED

        # Step 7: Determine evidence environment context
        evidence_envs = {c.historical_evidence.environment_context for c in all_candidates}
        if len(evidence_envs) == 1:
            historical_env = next(iter(evidence_envs))
        elif evidence_envs:
            historical_env = EnvironmentContext.MIXED
        else:
            historical_env = None

        has_evidence = any(
            c.historical_evidence.experience_count > 0 for c in all_candidates
        )

        log.info(
            "decision_analysis_complete",
            incident_id=context.incident_id,
            status=status,
            candidate_count=len(all_candidates),
            eligible_count=len(eligible),
            top_candidate=str(top_candidate.action_type) if top_candidate else None,
        )

        return DecisionAnalysis(
            decision_id=generate_decision_id(
                incident_id=context.incident_id,
                environment=str(context.environment),
                is_simulated=context.is_simulated,
                affected_services=context.affected_services,
            ),
            incident_id=context.incident_id,
            environment=context.environment,
            is_simulated=context.is_simulated,
            status=status,
            candidates=all_candidates,
            top_candidate=top_candidate,
            context_summary=self._build_context_summary(context),
            historical_evidence_available=has_evidence,
            historical_evidence_environment=historical_env,
            analysis_caveats=[
                "Decision relevance scores are NOT probabilities of success.",
                "Historical evidence describes past observations under comparable "
                "conditions — it is NOT causal proof and does NOT guarantee future outcomes.",
                "Current evidence takes precedence over historical patterns.",
                "All candidates require Safety/Policy evaluation and, where applicable, "
                "human authorization before any execution can occur.",
            ],
            rca_candidates_used=context.rca_top_candidates,
            experience_ids_used=sorted(set(all_experience_ids)),
        )

    def _enumerate_candidate_pairs(
        self, context: DecisionContext
    ) -> list[tuple[RecoveryActionType, str]]:
        """
        Generate bounded candidate (action_type, target_component) pairs.

        Actions come ONLY from RecoveryActionType vocabulary.
        Targets come ONLY from affected_services or RCA candidates.

        The set of (action, target) pairs is bounded and deterministic.
        MANUAL_INTERVENTION_REQUIRED is always included as a safe fallback.
        """
        # All valid targets: union of affected services and RCA candidates
        # Sorted for determinism
        candidate_targets = sorted(
            set(context.affected_services) | set(context.rca_top_candidates)
        )

        if not candidate_targets:
            return []

        pairs: list[tuple[RecoveryActionType, str]] = []

        # For each target, enumerate actions from the registry
        for target in candidate_targets:
            for action_type in sorted(RecoveryActionType, key=str):
                pairs.append((action_type, target))

        # Deterministic order: sort by (target, action_type)
        pairs.sort(key=lambda p: (p[1], str(p[0])))

        return pairs

    def _build_context_summary(self, context: DecisionContext) -> str:
        """Build a human-readable summary of the decision context."""
        parts = []

        if context.incident_id:
            parts.append(f"Incident: {context.incident_id}")

        env_label = "simulated" if context.is_simulated else "real"
        parts.append(f"Environment: {context.environment} ({env_label})")

        if context.affected_services:
            parts.append(f"Affected services: {', '.join(context.affected_services)}")

        if context.rca_top_candidates:
            parts.append(
                f"RCA top candidates: {', '.join(context.rca_top_candidates)}"
            )
        else:
            parts.append("No RCA candidates available")

        if context.active_event_count:
            parts.append(f"Active events: {context.active_event_count}")

        if context.reasoning_summary:
            parts.append(f"Reasoning: {context.reasoning_summary}")

        return ". ".join(parts) + "."
