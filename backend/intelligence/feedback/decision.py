from backend.intelligence.feedback.models import (
    DecisionState,
    EvidenceCompleteness,
    EvidenceConsistency,
    Feedback,
    LearningDecision,
    LearningSignal,
)


class DecisionEngine:
    """Deterministically evaluates if a LearningSignal is eligible for future learning."""

    def decide(self, feedback: Feedback, signal: LearningSignal) -> LearningDecision:
        """
        No LLM is used. Strict deterministic rules apply:
        - Simulated -> NOT_ELIGIBLE (for real-world learning)
        - UNKNOWN state -> NOT_ELIGIBLE
        - Conflicting / Partial -> DEFERRED
        - Verified Success/Failure with Complete + Consistent evidence -> ELIGIBLE
        """

        quality = feedback.quality

        if quality.is_simulated:
            decision_state = DecisionState.NOT_ELIGIBLE
            explanation = "Signal was generated from simulated execution. Not eligible for real-world learning."
        elif feedback.feedback_type == "UNKNOWN_SIGNAL":
            decision_state = DecisionState.NOT_ELIGIBLE
            explanation = "Outcome was UNKNOWN. Insufficient information to learn."
        elif quality.evidence_consistency == EvidenceConsistency.CONFLICTING:
            decision_state = DecisionState.DEFERRED
            explanation = "Evidence is conflicting. Decision deferred pending human review."
        elif quality.evidence_completeness == EvidenceCompleteness.MISSING:
            decision_state = DecisionState.NOT_ELIGIBLE
            explanation = "Missing evidence prevents safe learning."
        elif quality.evidence_consistency == EvidenceConsistency.CONSISTENT and quality.evidence_completeness == EvidenceCompleteness.COMPLETE:
            decision_state = DecisionState.ELIGIBLE
            explanation = "Verified outcome with consistent, complete evidence. Eligible for future learning ingestion."
        else:
            decision_state = DecisionState.UNKNOWN
            explanation = "Fell through quality heuristics."

        return LearningDecision(
            signal_id=signal.signal_id,
            decision_state=decision_state,
            explanation=explanation,
        )
