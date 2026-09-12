import pytest

from backend.intelligence.execution.models import ExecutionResult, ExecutionStatus
from backend.intelligence.outcomes.expected import ExpectedOutcomeResolver
from backend.intelligence.outcomes.models import Observation, OutcomeState
from backend.intelligence.outcomes.verification import VerificationEngine
from backend.intelligence.recovery.actions import RecoveryActionType


@pytest.fixture
def mock_execution() -> ExecutionResult:
    return ExecutionResult(
        execution_id="exec-123",
        plan_id="plan-123",
        approval_id="app-123",
        plan_hash="hash-123",
        action_type=RecoveryActionType.RESTART_SERVICE,
        target="service-a",
        executor_type="SimulatedRestartServiceExecutor",
        execution_mode="REAL",  # Start with REAL for deterministic testing
        status=ExecutionStatus.SUCCESS,
    )


@pytest.fixture
def verification_engine() -> VerificationEngine:
    return VerificationEngine()


def test_expected_outcome_resolver():
    assert ExpectedOutcomeResolver.resolve(RecoveryActionType.RESTART_SERVICE) == "HEALTHY"
    assert ExpectedOutcomeResolver.resolve(RecoveryActionType.SCALE_UP) == "CAPACITY_INCREASED_AND_HEALTHY"
    # Testing fallback for unmapped action
    assert ExpectedOutcomeResolver.resolve("UNKNOWN_ACTION") == "UNKNOWN_EXPECTED_STATE"


def test_verify_successful_observation(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    obs = Observation(
        execution_id=mock_execution.execution_id,
        plan_id=mock_execution.plan_id,
        plan_hash=mock_execution.plan_hash,
        observation_source="health_check",
        observed_state="HEALTHY",
    )

    assessment = verification_engine.verify(mock_execution, [obs])

    assert assessment.outcome_status == OutcomeState.VERIFIED_SUCCESS
    assert assessment.expected_outcome == "HEALTHY"
    assert assessment.observed_outcome == "HEALTHY"
    assert len(assessment.evidence) == 1
    assert assessment.evidence[0].comparison_matched is True
    assert assessment.is_simulated is False


def test_verify_failure_observation(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    obs = Observation(
        execution_id=mock_execution.execution_id,
        plan_id=mock_execution.plan_id,
        plan_hash=mock_execution.plan_hash,
        observation_source="health_check",
        observed_state="UNHEALTHY",
    )

    assessment = verification_engine.verify(mock_execution, [obs])

    assert assessment.outcome_status == OutcomeState.VERIFIED_FAILURE
    assert assessment.observed_outcome == "UNHEALTHY"
    assert len(assessment.evidence) == 1
    assert assessment.evidence[0].comparison_matched is False


def test_verify_conflicting_observations_yields_partial(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    obs1 = Observation(
        execution_id=mock_execution.execution_id,
        plan_id=mock_execution.plan_id,
        plan_hash=mock_execution.plan_hash,
        observation_source="health_check",
        observed_state="HEALTHY",
    )
    obs2 = Observation(
        execution_id=mock_execution.execution_id,
        plan_id=mock_execution.plan_id,
        plan_hash=mock_execution.plan_hash,
        observation_source="secondary_monitor",
        observed_state="UNHEALTHY",
    )

    assessment = verification_engine.verify(mock_execution, [obs1, obs2])

    assert assessment.outcome_status == OutcomeState.PARTIAL
    assert assessment.observed_outcome == "CONFLICTING_STATE"
    assert len(assessment.evidence) == 2
    assert assessment.evidence[0].comparison_matched is True
    assert assessment.evidence[1].comparison_matched is False


def test_verify_no_observations_yields_unknown(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    assessment = verification_engine.verify(mock_execution, [])

    assert assessment.outcome_status == OutcomeState.UNKNOWN
    assert assessment.observed_outcome == "NO_OBSERVATIONS"
    assert len(assessment.evidence) == 0


def test_verify_failed_execution_yields_failure_without_checking_evidence(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    mock_execution.status = ExecutionStatus.FAILED

    # Even if observation says healthy, execution explicitly failed
    obs = Observation(
        execution_id=mock_execution.execution_id,
        plan_id=mock_execution.plan_id,
        plan_hash=mock_execution.plan_hash,
        observation_source="health_check",
        observed_state="HEALTHY",
    )

    assessment = verification_engine.verify(mock_execution, [obs])

    assert assessment.outcome_status == OutcomeState.VERIFIED_FAILURE
    assert assessment.observed_outcome == "EXECUTION_FAILED"
    assert len(assessment.evidence) == 0


def test_verify_timeout_execution_yields_unknown(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    mock_execution.status = ExecutionStatus.TIMEOUT

    assessment = verification_engine.verify(mock_execution, [])

    assert assessment.outcome_status == OutcomeState.UNKNOWN
    assert assessment.observed_outcome == "EXECUTION_TIMEOUT"


def test_verify_simulated_execution_yields_unknown(verification_engine: VerificationEngine, mock_execution: ExecutionResult):
    mock_execution.execution_mode = "SIMULATED"

    obs = Observation(
        execution_id=mock_execution.execution_id,
        plan_id=mock_execution.plan_id,
        plan_hash=mock_execution.plan_hash,
        observation_source="health_check",
        observed_state="HEALTHY",
    )

    assessment = verification_engine.verify(mock_execution, [obs])

    assert assessment.outcome_status == OutcomeState.UNKNOWN
    assert assessment.observed_outcome == "SIMULATED_STATE"
    assert assessment.is_simulated is True
    # The evidence is still captured, but the final verdict is UNKNOWN because it was simulated
    assert len(assessment.evidence) == 1
