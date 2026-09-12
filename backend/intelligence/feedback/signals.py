from backend.intelligence.feedback.models import (
    CausalAttribution,
    Feedback,
    FeedbackType,
    LearningSignal,
    SignalType,
)
from backend.intelligence.outcomes.models import OutcomeState


class SignalGenerator:
    """Derives structured LearningSignals and Feedback from an OutcomeAssessment."""

    def generate_feedback(self, assessment) -> Feedback:
        """Determines FeedbackType and explicitly bounds CausalAttribution to OBSERVATIONAL."""
        from backend.intelligence.feedback.quality import FeedbackQualityAssessor

        quality = FeedbackQualityAssessor().assess(assessment)

        if assessment.outcome_status == OutcomeState.VERIFIED_SUCCESS:
            feedback_type = FeedbackType.SUCCESS_CONFIRMATION
            causal_attribution = CausalAttribution.OBSERVATIONAL
        elif assessment.outcome_status == OutcomeState.VERIFIED_FAILURE:
            feedback_type = FeedbackType.FAILURE_SIGNAL
            causal_attribution = CausalAttribution.OBSERVATIONAL
        elif assessment.outcome_status == OutcomeState.PARTIAL:
            feedback_type = FeedbackType.PARTIAL_SUCCESS_SIGNAL
            causal_attribution = CausalAttribution.OBSERVATIONAL
        else:
            feedback_type = FeedbackType.UNKNOWN_SIGNAL
            causal_attribution = CausalAttribution.NONE

        # Hard constraint: Never exceed OBSERVATIONAL in Phase 12.

        return Feedback(
            assessment_id=assessment.assessment_id,
            execution_id=assessment.execution_id,
            plan_id=assessment.plan_id,
            plan_hash=assessment.plan_hash,
            outcome_state=assessment.outcome_status,
            feedback_type=feedback_type,
            causal_attribution=causal_attribution,
            quality=quality,
        )

    def generate_signal(self, feedback: Feedback, assessment) -> LearningSignal:
        """Maps Feedback into a consumable LearningSignal."""

        if feedback.quality.is_simulated:
            signal_type = SignalType.ENGINEERING_TEST_SIGNAL
        elif feedback.feedback_type == FeedbackType.SUCCESS_CONFIRMATION:
            signal_type = SignalType.POSITIVE_EXPERIENCE
        elif feedback.feedback_type == FeedbackType.FAILURE_SIGNAL:
            signal_type = SignalType.NEGATIVE_EXPERIENCE
        elif feedback.feedback_type == FeedbackType.PARTIAL_SUCCESS_SIGNAL:
            signal_type = SignalType.UNEXPECTED_RESULT
        else:
            signal_type = SignalType.UNKNOWN_INFORMATION

        return LearningSignal(
            feedback_id=feedback.feedback_id,
            signal_type=signal_type,
            expected_result=assessment.expected_outcome,
            observed_result=assessment.observed_outcome,
            confidence=feedback.quality.confidence,
            is_simulated=feedback.quality.is_simulated,
        )
