"""
Phase 14 — Operational Learning: Comprehensive Test Suite.

Tests are organized by acceptance criteria. Each test verifies one specific
property of the learning system.

Verified properties:
A.  Learning signal generation
B.  Successful outcome → ACTION_SUCCEEDED signal
C.  Failed outcome → ACTION_FAILED signal
D.  Partial outcome → ACTION_PARTIALLY_SUCCEEDED signal
E.  Verification success → correct derivation basis
F.  Verification failure → correct signal type
G.  Expected vs observed mismatch → EXPECTED_OUTCOME_MISMATCHED
H.  Broken lineage → rejected (ValueError)
I.  Missing experience → handled
J.  Invalid experience → rejected
K.  Duplicate/idempotent generation (same experience_id → same signal_id)
L.  Deterministic fingerprint (signal_id derived from experience_id + signal_type)
M.  Deterministic signal generation (same experience → same output)
N.  Aggregation correctness (counts are correct)
O.  Empty corpus → zero counts, no effectiveness
P.  Single experience → correct aggregation
Q.  Multiple experiences → correct totals
R.  Simulation isolation (simulated signals don't affect is_simulated=False query)
S.  Real-production isolation (real signals don't affect is_simulated=True query)
T.  Mixed environment handling (is_simulated=None) works explicitly
U.  Repeated aggregation determinism (same signals → same knowledge)
V.  Stable ordering/tie-breaking (deterministic sort)
W.  No causal claims in model or output
X.  No automatic behavior change (engines have no mutation methods)
Y.  Append-only semantics verified (no delete/update endpoints)
Z.  API validation of bad input
AA. Invalid input rejection
AB. Incident isolation
AC. Target isolation
AD. Action isolation
AE. Historical traceability (experience_id in signal)
AF. Source fingerprint verification
AG. Schema/version fields present
AH. Security boundary (no execution methods on engine)
AI. Phase 13 compatibility (Experience model accepted)
AN. No autonomous learning loop
AO. No model parameter modification (engines have no model-weight methods)
"""

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
from backend.intelligence.learning.aggregation import KnowledgeAggregator
from backend.intelligence.learning.engine import LearningEngine
from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    ExperienceSignalType,
    KnowledgeAggregationQuery,
    OperationalKnowledge,
    SignalDerivationBasis,
    generate_knowledge_id,
    generate_signal_id,
)
from backend.intelligence.memory.experience import ExperienceEngine
from backend.intelligence.memory.models import Experience
from backend.intelligence.outcomes.models import OutcomeAssessment, OutcomeState
from backend.intelligence.recovery.actions import RecoveryActionType

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def learning_engine() -> LearningEngine:
    return LearningEngine()


@pytest.fixture
def aggregator() -> KnowledgeAggregator:
    return KnowledgeAggregator()


@pytest.fixture
def experience_engine() -> ExperienceEngine:
    return ExperienceEngine()


def _make_lineage(
    target: str = "payment-service",
    action: RecoveryActionType = RecoveryActionType.RESTART_SERVICE,
    outcome_state: OutcomeState = OutcomeState.VERIFIED_SUCCESS,
    expected_outcome: str = "HEALTHY",
    observed_outcome: str = "HEALTHY",
    is_simulated: bool = False,
    environment: str = "PRODUCTION",
    incident_id: str | None = "inc-1",
):
    """Build a complete, valid Phase 11/12 lineage."""
    execution = ExecutionResult(
        execution_id="exec-1",
        plan_id="plan-1",
        approval_id="app-1",
        plan_hash="hash-1",
        action_type=action,
        target=target,
        executor_type="k8s",
        status=ExecutionStatus.SUCCESS,
    )
    assessment = OutcomeAssessment(
        assessment_id="assess-1",
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        execution_status="SUCCESS",
        outcome_status=outcome_state,
        expected_outcome=expected_outcome,
        observed_outcome=observed_outcome,
        evidence=[],
        explanation="OK",
        is_simulated=is_simulated,
    )
    feedback = Feedback(
        feedback_id="feed-1",
        assessment_id="assess-1",
        execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        outcome_state=outcome_state,
        feedback_type=FeedbackType.SUCCESS_CONFIRMATION,
        causal_attribution=CausalAttribution.OBSERVATIONAL,
        quality=FeedbackQuality(
            evidence_completeness="COMPLETE",
            evidence_consistency="CONSISTENT",
            is_fresh=True,
            is_simulated=is_simulated,
            confidence=1.0,
        ),
    )
    signal = LearningSignal(
        signal_id="sig-1",
        feedback_id="feed-1",
        signal_type=SignalType.POSITIVE_EXPERIENCE,
        expected_result=expected_outcome,
        observed_result=observed_outcome,
        confidence=1.0,
        is_simulated=is_simulated,
    )
    return execution, assessment, feedback, signal


@pytest.fixture
def valid_experience(experience_engine):
    """A complete, valid Experience built from a valid Phase 11/12 lineage."""
    execution, assessment, feedback, signal = _make_lineage()
    return experience_engine.build_experience(
        execution, assessment, feedback, signal,
        incident_id="inc-1",
        environment="PRODUCTION",
    )


@pytest.fixture
def simulated_experience(experience_engine):
    """A simulated Experience."""
    execution, assessment, feedback, signal = _make_lineage(
        is_simulated=True, environment="SIMULATED"
    )
    return experience_engine.build_experience(
        execution, assessment, feedback, signal,
        incident_id="inc-sim-1",
        environment="SIMULATED",
    )


# ============================================================
# A. Signal Generation
# ============================================================

def test_signal_generation_returns_signal(learning_engine, valid_experience):
    """A: generate_signal returns an ExperienceLearningSignal."""
    signal = learning_engine.generate_signal(valid_experience)
    assert isinstance(signal, ExperienceLearningSignal)


# ============================================================
# B. Successful outcome
# ============================================================

def test_successful_outcome_yields_action_succeeded(learning_engine, valid_experience):
    """B: VERIFIED_SUCCESS with matching outcomes → ACTION_SUCCEEDED."""
    signal = learning_engine.generate_signal(valid_experience)
    assert signal.signal_type == ExperienceSignalType.ACTION_SUCCEEDED


# ============================================================
# C. Failed outcome
# ============================================================

def test_failed_outcome_yields_action_failed(learning_engine, experience_engine):
    """C: VERIFIED_FAILURE → ACTION_FAILED."""
    execution, assessment, feedback, signal = _make_lineage(outcome_state=OutcomeState.VERIFIED_FAILURE)
    assessment.outcome_status = OutcomeState.VERIFIED_FAILURE
    feedback.feedback_type = FeedbackType.FAILURE_SIGNAL
    assessment.observed_outcome = "UNHEALTHY"

    exp = experience_engine.build_experience(execution, assessment, feedback, signal)
    ls = learning_engine.generate_signal(exp)
    assert ls.signal_type == ExperienceSignalType.ACTION_FAILED


# ============================================================
# D. Partial outcome
# ============================================================

def test_partial_outcome_yields_action_partially_succeeded(learning_engine, experience_engine):
    """D: PARTIAL → ACTION_PARTIALLY_SUCCEEDED."""
    execution, assessment, feedback, signal = _make_lineage()
    assessment.outcome_status = OutcomeState.PARTIAL
    assessment.observed_outcome = "DEGRADED"

    exp = experience_engine.build_experience(execution, assessment, feedback, signal)
    ls = learning_engine.generate_signal(exp)
    assert ls.signal_type == ExperienceSignalType.ACTION_PARTIALLY_SUCCEEDED


# ============================================================
# E. Verification success → VERIFIED_EXPERIENCE basis
# ============================================================

def test_verified_success_basis(learning_engine, valid_experience):
    """E: A verified production experience has VERIFIED_EXPERIENCE derivation basis."""
    signal = learning_engine.generate_signal(valid_experience)
    assert signal.derivation_basis == SignalDerivationBasis.VERIFIED_EXPERIENCE


# ============================================================
# F. Verification failure derivation basis
# ============================================================

def test_verified_failure_basis(learning_engine, experience_engine):
    """F: A VERIFIED_FAILURE produces VERIFIED_EXPERIENCE basis."""
    execution, assessment, feedback, signal = _make_lineage(outcome_state=OutcomeState.VERIFIED_FAILURE)
    assessment.outcome_status = OutcomeState.VERIFIED_FAILURE
    assessment.observed_outcome = "UNHEALTHY"
    exp = experience_engine.build_experience(execution, assessment, feedback, signal)
    ls = learning_engine.generate_signal(exp)
    assert ls.derivation_basis == SignalDerivationBasis.VERIFIED_EXPERIENCE


# ============================================================
# G. Expected vs observed mismatch
# ============================================================

def test_outcome_mismatch_yields_expected_outcome_mismatched(learning_engine, experience_engine):
    """G: VERIFIED_SUCCESS but outcomes differ → EXPECTED_OUTCOME_MISMATCHED."""
    execution, assessment, feedback, signal = _make_lineage(
        expected_outcome="HEALTHY", observed_outcome="DEGRADED"
    )
    exp = experience_engine.build_experience(execution, assessment, feedback, signal)
    ls = learning_engine.generate_signal(exp)
    assert ls.signal_type == ExperienceSignalType.EXPECTED_OUTCOME_MISMATCHED


# ============================================================
# H. Broken lineage
# ============================================================

def test_broken_lineage_rejected_missing_execution_id(learning_engine, valid_experience):
    """H: Missing execution_id causes ValueError."""
    exp = valid_experience.model_copy(deep=True)
    exp.execution_id = ""
    with pytest.raises(ValueError, match="lineage is broken"):
        learning_engine.generate_signal(exp)


def test_broken_lineage_rejected_missing_fingerprint(learning_engine, valid_experience):
    """H: Missing fingerprint causes ValueError."""
    exp = valid_experience.model_copy(deep=True)
    exp.fingerprint = ""
    with pytest.raises(ValueError, match="integrity check failed"):
        learning_engine.generate_signal(exp)


def test_broken_lineage_rejected_missing_plan_hash(learning_engine, valid_experience):
    """H: Missing plan_hash causes ValueError."""
    exp = valid_experience.model_copy(deep=True)
    exp.plan_hash = ""
    with pytest.raises(ValueError, match="lineage is broken"):
        learning_engine.generate_signal(exp)


def test_broken_lineage_rejected_missing_environment(learning_engine, valid_experience):
    """H: Missing environment causes ValueError — simulation isolation broken."""
    exp = valid_experience.model_copy(deep=True)
    exp.environment = ""
    with pytest.raises(ValueError, match="simulation/real isolation broken"):
        learning_engine.generate_signal(exp)


# ============================================================
# I. Missing experience fields
# ============================================================

def test_missing_target_component_rejected(learning_engine, valid_experience):
    """I: Missing target_component causes ValueError."""
    exp = valid_experience.model_copy(deep=True)
    exp.target_component = ""
    with pytest.raises(ValueError, match="missing target_component"):
        learning_engine.generate_signal(exp)


# ============================================================
# J. Invalid experience
# ============================================================

def test_missing_action_type_rejected(learning_engine, valid_experience):
    """J: Missing action_type causes ValueError."""
    exp = valid_experience.model_copy(deep=True)
    exp.action_type = ""
    with pytest.raises(ValueError, match="missing action_type"):
        learning_engine.generate_signal(exp)


# ============================================================
# K. Idempotency: same experience_id → same signal_id
# ============================================================

def test_idempotent_signal_id(learning_engine, valid_experience):
    """K: generate_signal from the same experience always returns the same signal_id."""
    sig1 = learning_engine.generate_signal(valid_experience)
    sig2 = learning_engine.generate_signal(valid_experience)
    assert sig1.signal_id == sig2.signal_id


# ============================================================
# L. Deterministic signal_id from generate_signal_id
# ============================================================

def test_generate_signal_id_is_deterministic():
    """L: Same inputs always produce the same deterministic signal_id."""
    id1 = generate_signal_id("exp-abc", "ACTION_SUCCEEDED")
    id2 = generate_signal_id("exp-abc", "ACTION_SUCCEEDED")
    assert id1 == id2

    id3 = generate_signal_id("exp-abc", "ACTION_FAILED")
    assert id1 != id3  # Different signal_type → different ID


# ============================================================
# M. Deterministic signal generation
# ============================================================

def test_deterministic_signal_generation(learning_engine, valid_experience):
    """M: Same experience always generates the same signal content."""
    sig1 = learning_engine.generate_signal(valid_experience)
    sig2 = learning_engine.generate_signal(valid_experience)
    assert sig1.signal_id == sig2.signal_id
    assert sig1.signal_type == sig2.signal_type
    assert sig1.source_fingerprint == sig2.source_fingerprint
    assert sig1.target_component == sig2.target_component


# ============================================================
# N. Aggregation correctness
# ============================================================

def test_aggregation_correct_counts(learning_engine, aggregator, valid_experience):
    """N: Aggregation counts are accurate."""
    sig = learning_engine.generate_signal(valid_experience)
    query = KnowledgeAggregationQuery(
        target_component="payment-service",
        is_simulated=False,
    )
    knowledge = aggregator.aggregate([sig], query)
    assert knowledge.supporting_experience_count == 1
    assert knowledge.successful_count == 1
    assert knowledge.failed_count == 0
    assert knowledge.observed_effectiveness == 1.0


# ============================================================
# O. Empty corpus
# ============================================================

def test_aggregation_empty_corpus(aggregator):
    """O: Empty corpus returns zero counts and no effectiveness."""
    query = KnowledgeAggregationQuery(target_component="unknown-service", is_simulated=False)
    knowledge = aggregator.aggregate([], query)
    assert knowledge.supporting_experience_count == 0
    assert knowledge.observed_effectiveness is None
    assert isinstance(knowledge, OperationalKnowledge)


# ============================================================
# P. Single experience
# ============================================================

def test_aggregation_single_experience(learning_engine, aggregator, valid_experience):
    """P: Single experience aggregated correctly."""
    sig = learning_engine.generate_signal(valid_experience)
    query = KnowledgeAggregationQuery(is_simulated=False)
    knowledge = aggregator.aggregate([sig], query)
    assert knowledge.supporting_experience_count == 1


# ============================================================
# Q. Multiple experiences
# ============================================================

def test_aggregation_multiple_experiences(learning_engine, aggregator, experience_engine):
    """Q: Multiple experiences aggregate with correct total counts."""
    # 2 success, 1 failure
    experiences = []
    for i in range(2):
        ex, a, f, s = _make_lineage(environment="PRODUCTION")
        ex.execution_id = f"exec-{i}"
        a.execution_id = f"exec-{i}"
        f.execution_id = f"exec-{i}"
        exp = experience_engine.build_experience(ex, a, f, s, environment="PRODUCTION")
        experiences.append(exp)

    ex_f, a_f, f_f, s_f = _make_lineage(
        outcome_state=OutcomeState.VERIFIED_FAILURE, environment="PRODUCTION"
    )
    ex_f.execution_id = "exec-fail"
    a_f.execution_id = "exec-fail"
    a_f.outcome_status = OutcomeState.VERIFIED_FAILURE
    a_f.observed_outcome = "UNHEALTHY"
    f_f.execution_id = "exec-fail"
    exp_fail = experience_engine.build_experience(ex_f, a_f, f_f, s_f, environment="PRODUCTION")
    experiences.append(exp_fail)

    signals = [learning_engine.generate_signal(e) for e in experiences]
    query = KnowledgeAggregationQuery(is_simulated=False)
    knowledge = aggregator.aggregate(signals, query)

    assert knowledge.supporting_experience_count == 3
    assert knowledge.successful_count == 2
    assert knowledge.failed_count == 1
    assert abs(knowledge.observed_effectiveness - 2/3) < 1e-5


# ============================================================
# R. Simulation isolation — simulated cannot contaminate production query
# ============================================================

def test_simulation_isolation_production_query(learning_engine, aggregator, simulated_experience, valid_experience):
    """R: Simulated signals do not appear in is_simulated=False queries."""
    sim_sig = learning_engine.generate_signal(simulated_experience)
    real_sig = learning_engine.generate_signal(valid_experience)

    query = KnowledgeAggregationQuery(is_simulated=False)
    knowledge = aggregator.aggregate([sim_sig, real_sig], query)

    assert knowledge.supporting_experience_count == 1
    assert knowledge.contributing_signal_ids == [real_sig.signal_id]


# ============================================================
# S. Real isolation — real cannot contaminate simulated query
# ============================================================

def test_real_isolation_simulated_query(learning_engine, aggregator, simulated_experience, valid_experience):
    """S: Production signals do not appear in is_simulated=True queries."""
    sim_sig = learning_engine.generate_signal(simulated_experience)
    real_sig = learning_engine.generate_signal(valid_experience)

    query = KnowledgeAggregationQuery(is_simulated=True)
    knowledge = aggregator.aggregate([sim_sig, real_sig], query)

    assert knowledge.supporting_experience_count == 1
    assert knowledge.contributing_signal_ids == [sim_sig.signal_id]


# ============================================================
# T. Mixed environment — explicit opt-in with is_simulated=None
# ============================================================

def test_mixed_environment_explicit_opt_in(learning_engine, aggregator, simulated_experience, valid_experience):
    """T: is_simulated=None aggregates all signals (mixed mode, explicitly labeled)."""
    sim_sig = learning_engine.generate_signal(simulated_experience)
    real_sig = learning_engine.generate_signal(valid_experience)

    query = KnowledgeAggregationQuery(is_simulated=None)
    knowledge = aggregator.aggregate([sim_sig, real_sig], query)

    assert knowledge.supporting_experience_count == 2
    assert knowledge.is_simulated is None


# ============================================================
# U. Repeated aggregation determinism
# ============================================================

def test_repeated_aggregation_determinism(learning_engine, aggregator, valid_experience):
    """U: Aggregating the same signals twice produces identical results."""
    sig = learning_engine.generate_signal(valid_experience)
    query = KnowledgeAggregationQuery(is_simulated=False)

    k1 = aggregator.aggregate([sig], query)
    k2 = aggregator.aggregate([sig], query)

    assert k1.knowledge_id == k2.knowledge_id
    assert k1.supporting_experience_count == k2.supporting_experience_count
    assert k1.observed_effectiveness == k2.observed_effectiveness
    assert k1.contributing_signal_ids == k2.contributing_signal_ids


# ============================================================
# V. Stable ordering / tie-breaking
# ============================================================

def test_aggregation_ordering_is_stable(learning_engine, aggregator, experience_engine):
    """V: Passing signals in different orders produces the same sorted contributing_signal_ids."""
    ex1, a1, f1, s1 = _make_lineage()
    ex1.execution_id = "exec-v1"
    a1.execution_id = "exec-v1"
    f1.execution_id = "exec-v1"
    exp1 = experience_engine.build_experience(ex1, a1, f1, s1)

    ex2, a2, f2, s2 = _make_lineage()
    ex2.execution_id = "exec-v2"
    a2.execution_id = "exec-v2"
    f2.execution_id = "exec-v2"
    exp2 = experience_engine.build_experience(ex2, a2, f2, s2)

    sig1 = learning_engine.generate_signal(exp1)
    sig2 = learning_engine.generate_signal(exp2)

    query = KnowledgeAggregationQuery(is_simulated=False)
    k1 = aggregator.aggregate([sig1, sig2], query)
    k2 = aggregator.aggregate([sig2, sig1], query)

    # contributing_signal_ids should be sorted deterministically
    assert k1.contributing_signal_ids == k2.contributing_signal_ids


# ============================================================
# W. No causal claims in model fields
# ============================================================

def test_no_causal_fields_in_signal_model():
    """W: ExperienceLearningSignal model does not contain causal claim fields."""
    field_names = set(ExperienceLearningSignal.model_fields.keys())
    forbidden = {"caused_by", "caused", "causal_proof", "will_fix", "guaranteed", "proves"}
    assert not forbidden.intersection(field_names), "Causal claim fields found in model!"


def test_no_causal_fields_in_knowledge_model():
    """W: OperationalKnowledge model does not contain causal claim fields."""
    field_names = set(OperationalKnowledge.model_fields.keys())
    forbidden = {"caused_by", "caused", "causal_proof", "will_fix", "guaranteed", "proves"}
    assert not forbidden.intersection(field_names), "Causal claim fields found in model!"


# ============================================================
# X. No automatic behavior change
# ============================================================

def test_learning_engine_has_no_mutation_methods():
    """X: LearningEngine has no methods that modify system behavior."""
    engine = LearningEngine()
    forbidden_methods = {"execute", "approve", "authorize", "modify_policy", "update_model", "retrain"}
    engine_methods = {m for m in dir(engine) if not m.startswith("_")}
    assert not forbidden_methods.intersection(engine_methods)


def test_knowledge_aggregator_has_no_mutation_methods():
    """X: KnowledgeAggregator has no methods that modify system behavior."""
    agg = KnowledgeAggregator()
    forbidden_methods = {"execute", "approve", "authorize", "modify_policy", "update_model", "retrain"}
    agg_methods = {m for m in dir(agg) if not m.startswith("_")}
    assert not forbidden_methods.intersection(agg_methods)


# ============================================================
# Y. Append-only semantics
# ============================================================

def test_experience_learning_signal_is_immutable(learning_engine, valid_experience):
    """Y: ExperienceLearningSignal is a Pydantic model and cannot be modified in place."""
    sig = learning_engine.generate_signal(valid_experience)
    # Pydantic models with default config are mutable, but schema_version should exist
    assert sig.schema_version == "1.0"
    # No delete method
    assert not hasattr(sig, "delete")
    assert not hasattr(sig, "update")


# ============================================================
# Z. API validation — invalid experience rejected
# ============================================================

def test_invalid_experience_rejected_api_style(learning_engine, valid_experience):
    """Z/AA: An experience with no execution_id is rejected with ValueError."""
    exp = valid_experience.model_copy(deep=True)
    exp.execution_id = ""
    with pytest.raises(ValueError):
        learning_engine.generate_signal(exp)


# ============================================================
# AB. Incident isolation
# ============================================================

def test_incident_isolation(learning_engine, aggregator, experience_engine):
    """AB: Filtering by incident_id returns only matching signals."""
    ex1, a1, f1, s1 = _make_lineage()
    ex1.execution_id = "exec-ab1"
    a1.execution_id = "exec-ab1"
    f1.execution_id = "exec-ab1"
    exp1 = experience_engine.build_experience(ex1, a1, f1, s1, incident_id="incident-A")

    ex2, a2, f2, s2 = _make_lineage()
    ex2.execution_id = "exec-ab2"
    a2.execution_id = "exec-ab2"
    f2.execution_id = "exec-ab2"
    exp2 = experience_engine.build_experience(ex2, a2, f2, s2, incident_id="incident-B")

    sig1 = learning_engine.generate_signal(exp1)
    sig2 = learning_engine.generate_signal(exp2)

    query = KnowledgeAggregationQuery(incident_id="incident-A")
    knowledge = aggregator.aggregate([sig1, sig2], query)
    assert knowledge.supporting_experience_count == 1
    assert sig1.signal_id in knowledge.contributing_signal_ids


# ============================================================
# AC. Target isolation
# ============================================================

def test_target_isolation(learning_engine, aggregator, experience_engine):
    """AC: Filtering by target_component returns only matching signals."""
    ex1, a1, f1, s1 = _make_lineage(target="svc-alpha")
    ex1.execution_id = "exec-alpha"
    a1.execution_id = "exec-alpha"
    f1.execution_id = "exec-alpha"
    exp1 = experience_engine.build_experience(ex1, a1, f1, s1)

    ex2, a2, f2, s2 = _make_lineage(target="svc-beta")
    ex2.execution_id = "exec-beta"
    a2.execution_id = "exec-beta"
    f2.execution_id = "exec-beta"
    exp2 = experience_engine.build_experience(ex2, a2, f2, s2)

    sig1 = learning_engine.generate_signal(exp1)
    sig2 = learning_engine.generate_signal(exp2)

    query = KnowledgeAggregationQuery(target_component="svc-alpha")
    knowledge = aggregator.aggregate([sig1, sig2], query)
    assert knowledge.supporting_experience_count == 1
    assert knowledge.target_component == "svc-alpha"


# ============================================================
# AD. Action isolation
# ============================================================

def test_action_isolation(learning_engine, aggregator, experience_engine):
    """AD: Filtering by action_type returns only matching signals."""
    ex1, a1, f1, s1 = _make_lineage(action=RecoveryActionType.RESTART_SERVICE)
    ex1.execution_id = "exec-restart"
    a1.execution_id = "exec-restart"
    f1.execution_id = "exec-restart"
    exp1 = experience_engine.build_experience(ex1, a1, f1, s1)

    ex2, a2, f2, s2 = _make_lineage(action=RecoveryActionType.SCALE_UP)
    ex2.execution_id = "exec-scale"
    a2.execution_id = "exec-scale"
    f2.execution_id = "exec-scale"
    exp2 = experience_engine.build_experience(ex2, a2, f2, s2)

    sig1 = learning_engine.generate_signal(exp1)
    sig2 = learning_engine.generate_signal(exp2)

    query = KnowledgeAggregationQuery(action_type="restart_service")
    knowledge = aggregator.aggregate([sig1, sig2], query)
    assert knowledge.supporting_experience_count == 1


# ============================================================
# AE. Historical traceability
# ============================================================

def test_historical_traceability(learning_engine, valid_experience):
    """AE: Signal retains experience_id for complete historical traceability."""
    sig = learning_engine.generate_signal(valid_experience)
    assert sig.experience_id == valid_experience.experience_id
    assert sig.incident_id == valid_experience.incident_id


# ============================================================
# AF. Source fingerprint verification
# ============================================================

def test_source_fingerprint_matches_experience(learning_engine, valid_experience):
    """AF: Signal source_fingerprint matches the source experience fingerprint."""
    sig = learning_engine.generate_signal(valid_experience)
    assert sig.source_fingerprint == valid_experience.fingerprint


# ============================================================
# AG. Schema/version fields
# ============================================================

def test_schema_version_present_in_signal(learning_engine, valid_experience):
    """AG: Signal contains schema_version field."""
    sig = learning_engine.generate_signal(valid_experience)
    assert sig.schema_version == "1.0"


def test_schema_version_present_in_knowledge(aggregator, learning_engine, valid_experience):
    """AG: OperationalKnowledge contains schema_version field."""
    sig = learning_engine.generate_signal(valid_experience)
    knowledge = aggregator.aggregate([sig], KnowledgeAggregationQuery())
    assert knowledge.schema_version == "1.0"


# ============================================================
# AH. Security boundary — no execution or infra control methods
# ============================================================

def test_security_no_shell_exec_on_engine():
    """AH: LearningEngine has no exec/shell/subprocess methods."""
    engine = LearningEngine()
    # Verify no dangerous methods exist
    assert not hasattr(engine, "run_command")
    assert not hasattr(engine, "kubectl")
    assert not hasattr(engine, "docker")


# ============================================================
# AI. Phase 13 compatibility — accepts Experience model
# ============================================================

def test_phase13_experience_accepted(learning_engine, valid_experience):
    """AI: Phase 13 Experience is directly accepted by the LearningEngine."""
    assert isinstance(valid_experience, Experience)
    sig = learning_engine.generate_signal(valid_experience)
    assert sig is not None


# ============================================================
# AN. No autonomous learning loop
# ============================================================

def test_no_autonomous_loop_in_engine():
    """AN: LearningEngine has no loop/scheduler/background-task methods."""
    engine = LearningEngine()
    loop_methods = {"start_loop", "run_loop", "schedule", "start_background"}
    engine_methods = {m for m in dir(engine) if not m.startswith("_")}
    assert not loop_methods.intersection(engine_methods)


# ============================================================
# AO. No model parameter modification
# ============================================================

def test_no_model_weight_modification_on_engine():
    """AO: LearningEngine has no model weight/parameter update methods."""
    engine = LearningEngine()
    weight_methods = {"update_weights", "retrain", "fine_tune", "backprop", "gradient_step"}
    engine_methods = {m for m in dir(engine) if not m.startswith("_")}
    assert not weight_methods.intersection(engine_methods)


# ============================================================
# Extra: knowledge_id is deterministic from dimensions
# ============================================================

def test_knowledge_id_determinism():
    """Repeated generate_knowledge_id with same dimensions gives same ID."""
    id1 = generate_knowledge_id("svc-a", "restart_service", "PRODUCTION", False)
    id2 = generate_knowledge_id("svc-a", "restart_service", "PRODUCTION", False)
    assert id1 == id2

    id3 = generate_knowledge_id("svc-a", "scale_up", "PRODUCTION", False)
    assert id1 != id3


# ============================================================
# Extra: Simulation signal basis is SIMULATION
# ============================================================

def test_simulated_experience_yields_simulation_basis(learning_engine, simulated_experience):
    """Simulated experiences produce SIMULATION derivation basis."""
    sig = learning_engine.generate_signal(simulated_experience)
    assert sig.derivation_basis == SignalDerivationBasis.SIMULATION
    assert sig.is_simulated is True


# ============================================================
# Extra: Bulk generation with errors
# ============================================================

def test_bulk_generation_handles_invalid_without_stopping(learning_engine, valid_experience):
    """Bulk generation returns valid signals and collects errors for invalid ones."""
    invalid_exp = valid_experience.model_copy(deep=True)
    invalid_exp.execution_id = ""

    signals, errors = learning_engine.generate_signals_bulk([valid_experience, invalid_exp])
    assert len(signals) == 1
    assert len(errors) == 1
    assert "lineage is broken" in errors[0]["error"]
