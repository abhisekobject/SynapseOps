from datetime import UTC, datetime, timedelta

import pytest

from backend.intelligence.recovery.actions import RecoveryActionType
from backend.intelligence.recovery.models import RecoveryPlan, RecoveryStep
from backend.intelligence.safety.approval import ApprovalEngine
from backend.intelligence.safety.models import (
    ApprovalRequestResponse,
    ApprovalStatus,
    AuthorizationContext,
    PlanIntegrity,
    PolicyDecisionStatus,
)
from backend.intelligence.safety.policy import PolicyEngine


@pytest.fixture
def policy_engine() -> PolicyEngine:
    return PolicyEngine()


@pytest.fixture
def approval_engine() -> ApprovalEngine:
    return ApprovalEngine()


@pytest.fixture
def sample_plan() -> RecoveryPlan:
    return RecoveryPlan(
        plan_id="plan-1",
        incident_id="inc-1",
        overall_risk="MEDIUM",
        impact_analysis="Testing",
        steps=[
            RecoveryStep(
                action_type=RecoveryActionType.RESTART_SERVICE,
                target_component="service-a",
                estimated_risk="MEDIUM",
                justification="Test",
            )
        ],
    )


def test_plan_hash_integrity(sample_plan: RecoveryPlan):
    hash1 = PlanIntegrity.compute_hash(sample_plan)

    # Mutating an irrelevant field shouldn't exist in our canonical plan, but wait
    # Our canonicalization only includes plan_id, incident_id, steps(action, target, risk).

    # Mutating a critical field
    sample_plan.steps[0].target_component = "service-b"
    hash2 = PlanIntegrity.compute_hash(sample_plan)

    assert hash1 != hash2


def test_policy_engine_deny_unknown_action(policy_engine: PolicyEngine):
    # If a plan has an action not in the baseline, it's denied.
    plan = RecoveryPlan.model_construct(
        plan_id="plan-2",
        incident_id="inc-1",
        overall_risk="LOW",
        impact_analysis="Test",
        steps=[
            # We bypass Pydantic validation momentarily to test policy boundary
            RecoveryStep.model_construct(
                action_type="UNKNOWN_ACTION",
                target_component="service-a",
                estimated_risk="LOW",
                justification="Test",
            )
        ],
    )
    decision = policy_engine.evaluate(plan, "dummy-hash")
    assert decision.decision == PolicyDecisionStatus.DENY
    assert "Unknown or unsupported action type" in decision.reasons[0]


def test_policy_engine_low_risk(policy_engine: PolicyEngine):
    plan = RecoveryPlan(
        plan_id="plan-3",
        incident_id="inc-1",
        overall_risk="LOW",
        impact_analysis="Test",
        steps=[
            RecoveryStep(
                action_type=RecoveryActionType.SCALE_UP,
                target_component="service-a",
                estimated_risk="LOW",
                justification="Test",
            )
        ],
    )
    decision = policy_engine.evaluate(plan, "dummy-hash")
    assert decision.decision == PolicyDecisionStatus.ALLOW
    assert decision.risk_level == "LOW"


def test_policy_engine_requires_approval(policy_engine: PolicyEngine, sample_plan: RecoveryPlan):
    # RESTART_SERVICE is MEDIUM baseline
    decision = policy_engine.evaluate(sample_plan, "dummy-hash")
    assert decision.decision == PolicyDecisionStatus.REQUIRES_APPROVAL
    assert decision.risk_level == "MEDIUM"


def test_approval_separation_of_duties(approval_engine: ApprovalEngine):
    approval = ApprovalRequestResponse(
        approval_id="app-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        status=ApprovalStatus.PENDING,
        requested_by="user-a",
        requested_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    auth_requester = AuthorizationContext(principal="user-a", permissions=["recovery.plan.approve"])

    with pytest.raises(PermissionError, match="Separation of duties violation"):
        approval_engine.approve(approval, auth_requester, "hash-1")


def test_approval_hash_mismatch(approval_engine: ApprovalEngine):
    approval = ApprovalRequestResponse(
        approval_id="app-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        status=ApprovalStatus.PENDING,
        requested_by="user-a",
        requested_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    auth_approver = AuthorizationContext(principal="user-b", permissions=["recovery.plan.approve"])

    with pytest.raises(ValueError, match="Plan hash mismatch"):
        approval_engine.approve(approval, auth_approver, "hash-2")


def test_approval_expiration(approval_engine: ApprovalEngine):
    approval = ApprovalRequestResponse(
        approval_id="app-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        status=ApprovalStatus.PENDING,
        requested_by="user-a",
        requested_at=datetime.now(UTC) - timedelta(minutes=20),
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    auth_approver = AuthorizationContext(principal="user-b", permissions=["recovery.plan.approve"])

    with pytest.raises(ValueError, match="expired"):
        approval_engine.approve(approval, auth_approver, "hash-1")

    assert approval.status == ApprovalStatus.EXPIRED


def test_approval_success(approval_engine: ApprovalEngine):
    approval = ApprovalRequestResponse(
        approval_id="app-1",
        plan_id="plan-1",
        plan_hash="hash-1",
        status=ApprovalStatus.PENDING,
        requested_by="user-a",
        requested_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    auth_approver = AuthorizationContext(principal="user-b", permissions=["recovery.plan.approve"])

    result = approval_engine.approve(approval, auth_approver, "hash-1")
    assert result.status == ApprovalStatus.APPROVED
