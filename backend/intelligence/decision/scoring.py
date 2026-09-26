"""
Phase 16 — Adaptive Decision Intelligence: Decision Scoring.

Deterministic scoring of decision candidates using current evidence
and historical experience.

SCORING MODEL (documented):
    decision_relevance_score = weighted sum of component scores, normalized to [0.0, 1.0]

Component weights (must sum to 1.0):
    rca_alignment:          0.35  — Is the action target aligned with the RCA?
    historical_support:     0.30  — Does history show supporting outcomes?
    historical_verified:    0.15  — Are those outcomes verified (Phase 11)?
    risk_penalty:           0.10  — Higher risk reduces score
    evidence_volume:        0.10  — More evidence increases confidence

IMPORTANT:
    score = 0.82 means "0.82 decision relevance score under current evidence"
    It does NOT mean "82% probability of success".

DETERMINISM GUARANTEE:
    Same input → same score. No random components.
    Tie-breaking uses sorted action_type string, then target_component string.
"""

from __future__ import annotations

from backend.intelligence.decision.models import (
    CandidateEligibility,
    DecisionCandidate,
    EnvironmentContext,
    HistoricalEvidenceSummary,
)
from backend.intelligence.recovery.actions import (
    ACTION_REGISTRY,
    ActionRiskLevel,
    RecoveryActionType,
)

# Component weights (documented, must sum to 1.0)
_WEIGHT_RCA_ALIGNMENT = 0.35
_WEIGHT_HISTORICAL_SUPPORT = 0.30
_WEIGHT_HISTORICAL_VERIFIED = 0.15
_WEIGHT_RISK_PENALTY = 0.10
_WEIGHT_EVIDENCE_VOLUME = 0.10

assert abs(
    _WEIGHT_RCA_ALIGNMENT
    + _WEIGHT_HISTORICAL_SUPPORT
    + _WEIGHT_HISTORICAL_VERIFIED
    + _WEIGHT_RISK_PENALTY
    + _WEIGHT_EVIDENCE_VOLUME
    - 1.0
) < 1e-9, "Scoring weights must sum to 1.0"

# Risk penalty values (lower score = higher penalty)
_RISK_PENALTY = {
    ActionRiskLevel.LOW: 0.0,       # No penalty
    ActionRiskLevel.MEDIUM: 0.3,    # 30% penalty component
    ActionRiskLevel.HIGH: 0.7,      # 70% penalty component
}

# Evidence volume sigmoid-like scaling (capped)
_EVIDENCE_VOLUME_CAP = 20  # Beyond 20 experiences, full credit


class DecisionScorer:
    """
    Deterministic decision candidate scorer.

    BOUNDARY: This class only reads evidence and produces numeric scores.
    It does NOT execute, authorize, or modify any system state.
    """

    def score_candidate(
        self,
        *,
        action_type: RecoveryActionType,
        target_component: str,
        rca_candidates: list[str],
        rca_scores: dict[str, float],
        reasoning_recommended: list[str],
        historical_evidence: HistoricalEvidenceSummary,
        current_environment: EnvironmentContext,
    ) -> tuple[float, dict[str, float], list[str], list[str]]:
        """
        Score a decision candidate deterministically.

        Args:
            action_type: The recovery action being evaluated.
            target_component: The service this action would target.
            rca_candidates: Top services from RCA analysis.
            rca_scores: RCA scores per service.
            reasoning_recommended: Action types recommended by Phase 7 reasoning.
            historical_evidence: Retrieved historical evidence summary.
            current_environment: Current operational environment.

        Returns:
            Tuple of (score, breakdown, supporting_evidence, caveats)
            score: float in [0.0, 1.0]
            breakdown: dict of component name → component contribution
            supporting_evidence: list of evidence strings (for explanation)
            caveats: list of caveat strings (for honest uncertainty representation)
        """
        breakdown: dict[str, float] = {}
        evidence_list: list[str] = []
        caveats: list[str] = []

        # ----------------------------------------------------------------
        # Component 1: RCA alignment (0.35)
        # Does current RCA point to this target?
        # ----------------------------------------------------------------
        rca_score_val = 0.0
        if target_component in rca_candidates:
            # Get normalized RCA score for this component
            raw_rca = rca_scores.get(target_component, 0.0)
            # RCA scores are 0–1 already; use directly
            rca_score_val = min(raw_rca, 1.0)
            evidence_list.append(
                f"Current RCA identifies '{target_component}' as a candidate "
                f"root cause (score={raw_rca:.3f})"
            )
        else:
            caveats.append(
                f"Target component '{target_component}' is NOT in the current "
                f"RCA top candidates — historical evidence alone is insufficient "
                f"to support this action under current evidence."
            )

        breakdown["rca_alignment"] = round(rca_score_val * _WEIGHT_RCA_ALIGNMENT, 6)

        # ----------------------------------------------------------------
        # Component 2: Historical outcome support (0.30)
        # How often did this action historically produce supporting outcomes?
        # ----------------------------------------------------------------
        hist_score_val = 0.0
        if historical_evidence.is_sufficient and historical_evidence.observed_effectiveness is not None:
            hist_score_val = historical_evidence.observed_effectiveness
            evidence_list.append(
                f"Historical evidence: {historical_evidence.supporting_outcome_count} "
                f"supporting outcomes from {historical_evidence.experience_count} "
                f"relevant experiences "
                f"(observed effectiveness ratio: {hist_score_val:.3f})"
            )
            if historical_evidence.unsuccessful_outcome_count > 0:
                caveats.append(
                    f"Historical evidence also shows "
                    f"{historical_evidence.unsuccessful_outcome_count} unsuccessful "
                    f"outcome(s) — this disagreement is represented honestly."
                )
        elif not historical_evidence.is_sufficient:
            caveats.append(
                f"Insufficient historical evidence: "
                f"{historical_evidence.insufficiency_reason}"
            )

        breakdown["historical_support"] = round(hist_score_val * _WEIGHT_HISTORICAL_SUPPORT, 6)

        # ----------------------------------------------------------------
        # Component 3: Verified historical outcomes (0.15)
        # Phase 11 verification gives higher confidence than unverified outcomes
        # ----------------------------------------------------------------
        verified_score = 0.0
        if historical_evidence.experience_count > 0:
            verified_ratio = (
                historical_evidence.verified_experience_count
                / historical_evidence.experience_count
            )
            verified_score = verified_ratio
            if historical_evidence.verified_experience_count > 0:
                evidence_list.append(
                    f"{historical_evidence.verified_experience_count} of "
                    f"{historical_evidence.experience_count} historical experiences "
                    f"have Phase 11 verified outcomes"
                )
            else:
                caveats.append(
                    "No historical experiences have Phase 11 verified outcomes — "
                    "evidence is UNVERIFIED and should be treated with caution."
                )

        breakdown["historical_verified"] = round(verified_score * _WEIGHT_HISTORICAL_VERIFIED, 6)

        # ----------------------------------------------------------------
        # Component 4: Risk penalty (0.10)
        # Higher risk actions receive a scoring penalty
        # ----------------------------------------------------------------
        risk_info = ACTION_REGISTRY.get(action_type, {})
        risk_level = risk_info.get("risk_level", ActionRiskLevel.HIGH)
        penalty = _RISK_PENALTY.get(risk_level, 1.0)
        risk_contribution = (1.0 - penalty)
        breakdown["risk_penalty"] = round(risk_contribution * _WEIGHT_RISK_PENALTY, 6)

        if risk_level == ActionRiskLevel.HIGH:
            caveats.append(
                "This action has HIGH inherent risk — "
                "Safety/Policy requires human approval before execution."
            )

        # ----------------------------------------------------------------
        # Component 5: Evidence volume (0.10)
        # More evidence = more confidence in historical statistics
        # Capped at _EVIDENCE_VOLUME_CAP for scoring purposes
        # ----------------------------------------------------------------
        volume_score = min(
            historical_evidence.experience_count / _EVIDENCE_VOLUME_CAP,
            1.0,
        )
        breakdown["evidence_volume"] = round(volume_score * _WEIGHT_EVIDENCE_VOLUME, 6)

        # ----------------------------------------------------------------
        # Reasoning alignment bonus (not a separate weight, but affects evidence)
        # ----------------------------------------------------------------
        action_str = str(action_type)
        if action_str in [r.lower() for r in reasoning_recommended]:
            evidence_list.append(
                f"Phase 7 AI Incident Reasoning recommended action type "
                f"'{action_type}' for this incident"
            )

        # ----------------------------------------------------------------
        # Environment context caveat
        # ----------------------------------------------------------------
        if historical_evidence.environment_context == EnvironmentContext.SIMULATION:
            caveats.append(
                "All historical evidence comes from SIMULATION environments. "
                "Simulation evidence is included here because the current incident "
                "is also simulated. Do not extrapolate to real production behavior."
            )
        elif historical_evidence.environment_context == EnvironmentContext.MIXED:
            caveats.append(
                "Historical evidence is MIXED (simulation + real). "
                "Mixed evidence mode was explicitly requested. "
                "Treat with caution — simulation and real outcomes may differ."
            )

        # ----------------------------------------------------------------
        # Final composite score
        # ----------------------------------------------------------------
        total_score = sum(breakdown.values())
        total_score = round(min(max(total_score, 0.0), 1.0), 6)

        # Mandatory global caveat
        caveats.append(
            "Decision relevance score is NOT a probability of success. "
            "Historical evidence describes past observations, not future guarantees."
        )

        return total_score, breakdown, evidence_list, caveats

    def determine_eligibility(
        self,
        *,
        action_type: RecoveryActionType,
        target_component: str,
        rca_candidates: list[str],
        historical_evidence: HistoricalEvidenceSummary,
        score: float,
        current_environment: EnvironmentContext,
        allow_simulation_evidence: bool,
    ) -> tuple[CandidateEligibility, list[str]]:
        """
        Determine whether a candidate is eligible for referral to Safety/Policy.

        Eligibility is NOT the same as authorization. It means:
        "This candidate passes the decision-layer gate and is ready for
        the existing Safety/Policy pipeline."

        Returns:
            (eligibility_status, reasons)
        """
        reasons: list[str] = []

        # Gate 1: Real incident with no real evidence (and simulation not allowed)
        if (
            current_environment == EnvironmentContext.REAL
            and not allow_simulation_evidence
            and historical_evidence.environment_context == EnvironmentContext.SIMULATION
            and historical_evidence.experience_count > 0
        ):
            return (
                CandidateEligibility.INELIGIBLE_ENV_MISMATCH,
                [
                    "Simulation evidence cannot support a real-environment decision "
                    "without explicit allow_simulation_evidence=True."
                ],
            )

        # Gate 2: Current RCA does not support this target at all
        # (We allow it but flag it — do not block entirely since RCA can miss things)
        if target_component not in rca_candidates and not historical_evidence.is_sufficient:
            return (
                CandidateEligibility.INELIGIBLE_NO_EVIDENCE,
                [
                    f"Target '{target_component}' is not identified by current RCA, "
                    f"and there is insufficient historical evidence. "
                    f"Cannot support this candidate under current evidence."
                ],
            )

        # All gates passed
        if rca_candidates and target_component in rca_candidates:
            reasons.append(f"Target '{target_component}' is supported by current RCA analysis")
        if historical_evidence.is_sufficient:
            reasons.append(
                f"Sufficient historical evidence: {historical_evidence.experience_count} "
                f"experience(s) available"
            )
        reasons.append(
            "Candidate is eligible for referral to the Safety/Policy pipeline. "
            "Final authorization requires Safety evaluation and, where applicable, "
            "human approval."
        )

        return CandidateEligibility.ELIGIBLE, reasons

    def build_candidate(
        self,
        *,
        action_type: RecoveryActionType,
        target_component: str,
        rca_candidates: list[str],
        rca_scores: dict[str, float],
        reasoning_recommended: list[str],
        historical_evidence: HistoricalEvidenceSummary,
        current_environment: EnvironmentContext,
        allow_simulation_evidence: bool,
    ) -> DecisionCandidate:
        """
        Build a fully scored and annotated DecisionCandidate.

        This is the main entry point — calls score_candidate and determine_eligibility,
        then assembles the complete candidate object.
        """
        # Score
        score, breakdown, evidence_list, caveats = self.score_candidate(
            action_type=action_type,
            target_component=target_component,
            rca_candidates=rca_candidates,
            rca_scores=rca_scores,
            reasoning_recommended=reasoning_recommended,
            historical_evidence=historical_evidence,
            current_environment=current_environment,
        )

        # Eligibility
        eligibility, eligibility_reasons = self.determine_eligibility(
            action_type=action_type,
            target_component=target_component,
            rca_candidates=rca_candidates,
            historical_evidence=historical_evidence,
            score=score,
            current_environment=current_environment,
            allow_simulation_evidence=allow_simulation_evidence,
        )

        # Risk level and reversibility from the action registry
        risk_info = ACTION_REGISTRY.get(action_type, {})
        risk_level = risk_info.get("risk_level", ActionRiskLevel.HIGH)
        # Reversibility heuristic based on action type
        reversible = action_type not in {
            RecoveryActionType.ROLLBACK_DEPLOYMENT,
            RecoveryActionType.BLOCK_TRAFFIC,
        }

        # Verification requirements based on action type
        verification_reqs = self._build_verification_requirements(action_type, target_component)

        return DecisionCandidate(
            action_type=action_type,
            target_component=target_component,
            risk_level=risk_level,
            is_reversible=reversible,
            decision_relevance_score=score,
            score_breakdown=breakdown,
            historical_evidence=historical_evidence,
            eligibility=eligibility,
            eligibility_reasons=eligibility_reasons,
            supporting_evidence=evidence_list,
            caveats=caveats,
            verification_requirements=verification_reqs,
            rca_alignment_services=[
                s for s in rca_candidates if s == target_component
            ],
        )

    def _build_verification_requirements(
        self, action_type: RecoveryActionType, target_component: str
    ) -> list[str]:
        """Build a list of expected verification conditions for this action."""
        base = [f"Service '{target_component}' returns to healthy status"]
        if action_type == RecoveryActionType.RESTART_SERVICE:
            return base + [
                f"'{target_component}' passes health check within timeout",
                "Error rate returns below threshold",
                "Latency returns to normal range",
            ]
        if action_type == RecoveryActionType.SCALE_UP:
            return base + [
                "Replica count increased to target",
                "Load distribution improves",
            ]
        if action_type == RecoveryActionType.ROLLBACK_DEPLOYMENT:
            return base + [
                "Deployment version reverted to last-known-good",
                "No new errors introduced by rollback",
            ]
        if action_type == RecoveryActionType.CLEAR_CACHE:
            return base + [
                "Cache invalidated successfully",
                "Downstream services resume normal operation",
            ]
        if action_type == RecoveryActionType.BLOCK_TRAFFIC:
            return base + [
                "Traffic routing updated",
                "Dependent services no longer receive failed requests",
            ]
        return base
