from backend.intelligence.execution.models import ExecutionResult, ExecutionStatus
from backend.intelligence.outcomes.expected import ExpectedOutcomeResolver
from backend.intelligence.outcomes.models import (
    Evidence,
    Observation,
    OutcomeAssessment,
    OutcomeState,
)


class VerificationEngine:
    """Deterministically verifies if observations match the expected outcome."""

    def verify(self, execution: ExecutionResult, observations: list[Observation]) -> OutcomeAssessment:
        """
        Assesses what actually happened based on execution record and concrete evidence.
        """

        # 1. Resolve Expected Outcome
        expected_outcome = ExpectedOutcomeResolver.resolve(execution.action_type)

        # 2. Check Execution Status
        if execution.status != ExecutionStatus.SUCCESS:
            return self._build_assessment(
                execution=execution,
                outcome_status=OutcomeState.UNKNOWN if execution.status == ExecutionStatus.TIMEOUT else OutcomeState.VERIFIED_FAILURE,
                expected=expected_outcome,
                observed="EXECUTION_FAILED" if execution.status != ExecutionStatus.TIMEOUT else "EXECUTION_TIMEOUT",
                evidence=[],
                explanation=f"Execution did not succeed (Status: {execution.status})."
            )

        # 3. Handle No Observations
        if not observations:
            return self._build_assessment(
                execution=execution,
                outcome_status=OutcomeState.UNKNOWN,
                expected=expected_outcome,
                observed="NO_OBSERVATIONS",
                evidence=[],
                explanation="Execution succeeded, but no observations were provided to verify the outcome."
            )

        # 4. Check for Simulated Observations / Execution
        # If the execution was simulated, we cannot definitively prove real-world state.
        is_simulated = execution.execution_mode == "SIMULATED" or any(obs.metadata.get("is_simulated") for obs in observations)

        evidence_list = []
        all_matched = True
        any_matched = False

        for obs in observations:
            matched = obs.observed_state.upper() == expected_outcome.upper()
            all_matched = all_matched and matched
            any_matched = any_matched or matched

            evidence_list.append(
                Evidence(
                    observation_id=obs.observation_id,
                    source=obs.observation_source,
                    expected_value=expected_outcome,
                    observed_value=obs.observed_state,
                    comparison_matched=matched,
                )
            )

        if is_simulated:
            outcome_status = OutcomeState.UNKNOWN
            explanation = "Execution/Observation was simulated. Real-world outcome is fundamentally UNKNOWN."
            observed_str = "SIMULATED_STATE"
        elif all_matched:
            outcome_status = OutcomeState.VERIFIED_SUCCESS
            explanation = "All evidence deterministically matches the expected outcome."
            observed_str = expected_outcome
        elif any_matched:
            outcome_status = OutcomeState.PARTIAL
            explanation = "Conflicting evidence: Some observations matched, others did not."
            observed_str = "CONFLICTING_STATE"
        else:
            outcome_status = OutcomeState.VERIFIED_FAILURE
            explanation = "Evidence explicitly contradicts the expected outcome."
            observed_str = observations[0].observed_state  # Just take the first failure state for brevity

        return self._build_assessment(
            execution=execution,
            outcome_status=outcome_status,
            expected=expected_outcome,
            observed=observed_str,
            evidence=evidence_list,
            explanation=explanation,
            is_simulated=is_simulated,
        )

    def _build_assessment(
        self,
        execution: ExecutionResult,
        outcome_status: OutcomeState,
        expected: str,
        observed: str,
        evidence: list[Evidence],
        explanation: str,
        is_simulated: bool = False,
    ) -> OutcomeAssessment:

        return OutcomeAssessment(
            execution_id=execution.execution_id,
            plan_id=execution.plan_id,
            plan_hash=execution.plan_hash,
            execution_status=execution.status,
            outcome_status=outcome_status,
            expected_outcome=expected,
            observed_outcome=observed,
            evidence=evidence,
            explanation=explanation,
            is_simulated=is_simulated or execution.execution_mode == "SIMULATED",
        )
