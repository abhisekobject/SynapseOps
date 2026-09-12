from backend.intelligence.execution.models import ExecutionResult
from backend.intelligence.feedback.models import Feedback, LearningSignal
from backend.intelligence.memory.fingerprint import FingerprintGenerator
from backend.intelligence.memory.models import Experience
from backend.intelligence.outcomes.models import OutcomeAssessment


class ExperienceEngine:
    """Builds a historical Experience from Phase 11/12 lineage artifacts."""

    def build_experience(
        self,
        execution: ExecutionResult,
        assessment: OutcomeAssessment,
        feedback: Feedback,
        signal: LearningSignal,
        incident_id: str | None = None,
        environment: str | None = None,
    ) -> Experience:
        """
        Deterministically builds an Experience episode.
        Validates lineage explicitly.
        """
        # Validate Lineage
        if assessment.execution_id != execution.execution_id:
            raise ValueError("Mismatched Execution ID in Lineage")
        if feedback.assessment_id != assessment.assessment_id:
            raise ValueError("Mismatched Assessment ID in Lineage")
        if signal.feedback_id != feedback.feedback_id:
            raise ValueError("Mismatched Feedback ID in Lineage")
        if assessment.plan_hash != execution.plan_hash:
            raise ValueError("Mismatched Plan Hash in Lineage")

        action_type = str(execution.action_type)
        outcome_state = str(assessment.outcome_status)
        feedback_type = str(feedback.feedback_type)
        learning_signal_type = str(signal.signal_type)

        if not environment:
            environment = "SIMULATED" if signal.is_simulated else "PRODUCTION"

        fingerprint = FingerprintGenerator.generate(
            target_component=execution.target,
            action_type=action_type,
            expected_outcome=assessment.expected_outcome,
            observed_outcome=assessment.observed_outcome,
            outcome_state=outcome_state,
            feedback_type=feedback_type,
            learning_signal_type=learning_signal_type,
            is_simulated=signal.is_simulated,
            environment=environment,
        )

        return Experience(
            incident_id=incident_id,
            learning_signal_id=signal.signal_id,
            feedback_id=feedback.feedback_id,
            assessment_id=assessment.assessment_id,
            execution_id=execution.execution_id,
            plan_id=execution.plan_id,
            plan_hash=execution.plan_hash,
            target_component=execution.target,
            action_type=action_type,
            expected_outcome=assessment.expected_outcome,
            observed_outcome=assessment.observed_outcome,
            outcome_state=outcome_state,
            feedback_type=feedback_type,
            learning_signal_type=learning_signal_type,
            is_simulated=signal.is_simulated,
            environment=environment,
            fingerprint=fingerprint,
        )
