
import pytest

from backend.intelligence.feedback.decision import DecisionEngine
from backend.intelligence.feedback.models import DecisionState, FeedbackType, SignalType
from backend.intelligence.feedback.signals import SignalGenerator
from backend.intelligence.outcomes.models import Evidence, OutcomeAssessment, OutcomeState


@pytest.fixture
def signal_generator() -> SignalGenerator:
    return SignalGenerator()


@pytest.fixture
def decision_engine() -> DecisionEngine:
    return DecisionEngine()


@pytest.fixture
def mock_assessment_success() -> OutcomeAssessment:
    return OutcomeAssessment(
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        execution_status="SUCCESS",
        outcome_status=OutcomeState.VERIFIED_SUCCESS,
        expected_outcome="HEALTHY",
        observed_outcome="HEALTHY",
        evidence=[Evidence(observation_id="obs-1", source="health_check", expected_value="HEALTHY", observed_value="HEALTHY", comparison_matched=True)],
        explanation="Success verified",
        is_simulated=False,
    )


@pytest.fixture
def mock_assessment_failure() -> OutcomeAssessment:
    return OutcomeAssessment(
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        execution_status="SUCCESS",
        outcome_status=OutcomeState.VERIFIED_FAILURE,
        expected_outcome="HEALTHY",
        observed_outcome="UNHEALTHY",
        evidence=[Evidence(observation_id="obs-1", source="health_check", expected_value="HEALTHY", observed_value="UNHEALTHY", comparison_matched=False)],
        explanation="Failure verified",
        is_simulated=False,
    )


@pytest.fixture
def mock_assessment_unknown() -> OutcomeAssessment:
    return OutcomeAssessment(
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        execution_status="SUCCESS",
        outcome_status=OutcomeState.UNKNOWN,
        expected_outcome="HEALTHY",
        observed_outcome="UNKNOWN",
        evidence=[],
        explanation="No evidence",
        is_simulated=False,
    )


def test_verified_success_generates_positive_learning_signal(
    signal_generator: SignalGenerator,
    decision_engine: DecisionEngine,
    mock_assessment_success: OutcomeAssessment
):
    feedback = signal_generator.generate_feedback(mock_assessment_success)
    assert feedback.feedback_type == FeedbackType.SUCCESS_CONFIRMATION
    assert feedback.causal_attribution == "OBSERVATIONAL"
    assert feedback.quality.evidence_completeness == "COMPLETE"

    signal = signal_generator.generate_signal(feedback, mock_assessment_success)
    assert signal.signal_type == SignalType.POSITIVE_EXPERIENCE

    decision = decision_engine.decide(feedback, signal)
    assert decision.decision_state == DecisionState.ELIGIBLE


def test_verified_failure_generates_negative_learning_signal(
    signal_generator: SignalGenerator,
    decision_engine: DecisionEngine,
    mock_assessment_failure: OutcomeAssessment
):
    feedback = signal_generator.generate_feedback(mock_assessment_failure)
    assert feedback.feedback_type == FeedbackType.FAILURE_SIGNAL

    signal = signal_generator.generate_signal(feedback, mock_assessment_failure)
    assert signal.signal_type == SignalType.NEGATIVE_EXPERIENCE

    decision = decision_engine.decide(feedback, signal)
    assert decision.decision_state == DecisionState.ELIGIBLE


def test_unknown_assessment_not_eligible(
    signal_generator: SignalGenerator,
    decision_engine: DecisionEngine,
    mock_assessment_unknown: OutcomeAssessment
):
    feedback = signal_generator.generate_feedback(mock_assessment_unknown)
    assert feedback.feedback_type == FeedbackType.UNKNOWN_SIGNAL
    assert feedback.quality.evidence_completeness == "MISSING"

    signal = signal_generator.generate_signal(feedback, mock_assessment_unknown)
    assert signal.signal_type == SignalType.UNKNOWN_INFORMATION

    decision = decision_engine.decide(feedback, signal)
    assert decision.decision_state == DecisionState.NOT_ELIGIBLE


def test_simulated_outcome_yields_engineering_test_and_not_eligible(
    signal_generator: SignalGenerator,
    decision_engine: DecisionEngine,
    mock_assessment_success: OutcomeAssessment
):
    mock_assessment_success.is_simulated = True

    feedback = signal_generator.generate_feedback(mock_assessment_success)
    assert feedback.quality.is_simulated is True

    signal = signal_generator.generate_signal(feedback, mock_assessment_success)
    assert signal.signal_type == SignalType.ENGINEERING_TEST_SIGNAL
    assert signal.is_simulated is True

    decision = decision_engine.decide(feedback, signal)
    assert decision.decision_state == DecisionState.NOT_ELIGIBLE
    assert "simulated" in decision.explanation.lower()
