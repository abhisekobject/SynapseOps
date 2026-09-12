import pytest

from backend.intelligence.execution.models import ExecutionResult, ExecutionStatus
from backend.intelligence.feedback.models import (
    CausalAttribution,
    Feedback,
    FeedbackQuality,
    FeedbackType,
    LearningSignal,
    SignalType,
)
from backend.intelligence.memory.experience import ExperienceEngine
from backend.intelligence.memory.models import RetrievalQuery
from backend.intelligence.memory.retrieval import RetrievalEngine
from backend.intelligence.outcomes.models import OutcomeAssessment, OutcomeState
from backend.intelligence.recovery.actions import RecoveryActionType


@pytest.fixture
def experience_engine() -> ExperienceEngine:
    return ExperienceEngine()


@pytest.fixture
def retrieval_engine() -> RetrievalEngine:
    return RetrievalEngine()


@pytest.fixture
def valid_lineage():
    execution = ExecutionResult(
        execution_id="exec-1",
        plan_id="plan-1",
        approval_id="app-1",
        plan_hash="hash-1",
        action_type=RecoveryActionType.RESTART_SERVICE,
        target="payment-service",
        executor_type="k8s",
        status=ExecutionStatus.SUCCESS,
    )

    assessment = OutcomeAssessment(
        assessment_id="assess-1",
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        execution_status="SUCCESS",
        outcome_status=OutcomeState.VERIFIED_SUCCESS,
        expected_outcome="HEALTHY",
        observed_outcome="HEALTHY",
        evidence=[],
        explanation="OK",
        is_simulated=False,
    )

    feedback = Feedback(
        feedback_id="feed-1",
        assessment_id="assess-1",
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        outcome_state=OutcomeState.VERIFIED_SUCCESS,
        feedback_type=FeedbackType.SUCCESS_CONFIRMATION,
        causal_attribution=CausalAttribution.OBSERVATIONAL,
        quality=FeedbackQuality(
            evidence_completeness="COMPLETE",
            evidence_consistency="CONSISTENT",
            is_fresh=True,
            is_simulated=False,
            confidence=1.0,
        )
    )

    signal = LearningSignal(
        signal_id="sig-1",
        feedback_id="feed-1",
        signal_type=SignalType.POSITIVE_EXPERIENCE,
        expected_result="HEALTHY",
        observed_result="HEALTHY",
        confidence=1.0,
        is_simulated=False,
    )

    return execution, assessment, feedback, signal


def test_experience_builder_valid_lineage(experience_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage

    experience = experience_engine.build_experience(execution, assessment, feedback, signal)

    assert experience.learning_signal_id == signal.signal_id
    assert experience.target_component == "payment-service"
    assert experience.action_type == "restart_service"
    assert experience.outcome_state == "VERIFIED_SUCCESS"
    assert experience.is_simulated is False
    assert experience.fingerprint is not None


def test_experience_builder_rejects_mismatched_execution(experience_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage
    assessment.execution_id = "exec-WRONG"

    with pytest.raises(ValueError, match="Mismatched Execution ID"):
        experience_engine.build_experience(execution, assessment, feedback, signal)


def test_experience_builder_rejects_mismatched_feedback(experience_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage
    feedback.assessment_id = "assess-WRONG"

    with pytest.raises(ValueError, match="Mismatched Assessment ID"):
        experience_engine.build_experience(execution, assessment, feedback, signal)


def test_retrieval_engine_exact_match(experience_engine, retrieval_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage
    exp1 = experience_engine.build_experience(execution, assessment, feedback, signal)

    query = RetrievalQuery(
        target_component="payment-service",
        action_type=RecoveryActionType.RESTART_SERVICE,
    )

    result = retrieval_engine.retrieve(query, [exp1])

    assert len(result.results) == 1
    retrieved = result.results[0]

    assert retrieved.experience.experience_id == exp1.experience_id
    assert retrieved.relevance.score == 35  # target (+20) + action (+15)
    assert "MATCH: target_component" in retrieved.relevance.reasons
    assert "MATCH: action_type" in retrieved.relevance.reasons


def test_retrieval_engine_simulation_mismatch_penalty(experience_engine, retrieval_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage
    signal.is_simulated = True  # Make it an engineering test
    exp_sim = experience_engine.build_experience(execution, assessment, feedback, signal)

    # Query explicitly asks for REAL experiences
    query = RetrievalQuery(
        target_component="payment-service",
        is_simulated=False,
    )

    result = retrieval_engine.retrieve(query, [exp_sim])

    # Score should be target (+20) + mismatch (-50) = -30
    # Because it is < 0, it should be excluded from results.
    assert len(result.results) == 0


def test_retrieval_engine_ordering(experience_engine, retrieval_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage
    exp_perfect = experience_engine.build_experience(execution, assessment, feedback, signal)

    # Create an exp with a different target but same action
    execution_partial = execution.model_copy(deep=True)
    execution_partial.target = "other-service"
    exp_partial = experience_engine.build_experience(execution_partial, assessment, feedback, signal)

    query = RetrievalQuery(
        target_component="payment-service",
        action_type=RecoveryActionType.RESTART_SERVICE,
    )

    result = retrieval_engine.retrieve(query, [exp_partial, exp_perfect])

    assert len(result.results) == 2
    # Perfect match should be first (score 35)
    assert result.results[0].experience.experience_id == exp_perfect.experience_id
    assert result.results[0].relevance.score == 35

    # Partial match should be second (score 15 for just action match)
    assert result.results[1].experience.experience_id == exp_partial.experience_id
    assert result.results[1].relevance.score == 15


def test_retrieval_engine_environment_match(experience_engine, retrieval_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage
    exp = experience_engine.build_experience(execution, assessment, feedback, signal, environment="PRODUCTION")

    query = RetrievalQuery(
        target_component="payment-service",
        environment="PRODUCTION"
    )

    result = retrieval_engine.retrieve(query, [exp])
    assert len(result.results) == 1
    assert result.results[0].relevance.score == 30 # target (+20) + environment (+10)


def test_retrieval_engine_tie_breaking(experience_engine, retrieval_engine, valid_lineage):
    execution, assessment, feedback, signal = valid_lineage

    # Create two identical experiences (they will get different experience_ids but same semantic content)
    exp1 = experience_engine.build_experience(execution, assessment, feedback, signal)
    exp2 = experience_engine.build_experience(execution, assessment, feedback, signal)

    query = RetrievalQuery(
        target_component="payment-service"
    )

    # Pass in random order
    result = retrieval_engine.retrieve(query, [exp2, exp1])

    assert len(result.results) == 2
    assert result.results[0].relevance.score == result.results[1].relevance.score

    # Must be ordered by experience_id ASC ascending for tie breaker
    assert result.results[0].experience.experience_id < result.results[1].experience.experience_id


def test_fingerprint_determinism():
    from backend.intelligence.memory.fingerprint import FingerprintGenerator

    # Same inputs must produce exact same hash
    hash1 = FingerprintGenerator.generate(
        target_component="svc-a",
        action_type="restart",
        expected_outcome="ok",
        observed_outcome="ok",
        outcome_state="VERIFIED_SUCCESS",
        feedback_type="SUCCESS_CONFIRMATION",
        learning_signal_type="POSITIVE_EXPERIENCE",
        is_simulated=False,
        environment="PRODUCTION"
    )

    hash2 = FingerprintGenerator.generate(
        target_component="svc-a",
        action_type="restart",
        expected_outcome="ok",
        observed_outcome="ok",
        outcome_state="VERIFIED_SUCCESS",
        feedback_type="SUCCESS_CONFIRMATION",
        learning_signal_type="POSITIVE_EXPERIENCE",
        is_simulated=False,
        environment="PRODUCTION"
    )

    assert hash1 == hash2

    # Small change produces totally different hash
    hash3 = FingerprintGenerator.generate(
        target_component="svc-a",
        action_type="restart",
        expected_outcome="ok",
        observed_outcome="ok",
        outcome_state="VERIFIED_SUCCESS",
        feedback_type="SUCCESS_CONFIRMATION",
        learning_signal_type="POSITIVE_EXPERIENCE",
        is_simulated=False,
        environment="STAGING"
    )

    assert hash1 != hash3
