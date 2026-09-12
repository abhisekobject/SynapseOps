from datetime import UTC, datetime, timedelta

import pytest

from backend.intelligence.execution.adapters import ExecutionAdapter
from backend.intelligence.execution.engine import ExecutionEngine
from backend.intelligence.execution.gate import AuthorizationError, ExecutionGate, IntegrityError
from backend.intelligence.execution.models import ExecutionAuthorization, ExecutionStatus
from backend.intelligence.execution.registry import ExecutorRegistry
from backend.intelligence.recovery.actions import RecoveryActionType
from backend.intelligence.recovery.models import RecoveryPlan, RecoveryStep
from backend.intelligence.safety.models import (
    ApprovalRequestResponse,
    ApprovalStatus,
    AuthorizationContext,
    PlanIntegrity,
)


@pytest.fixture
def auth_context() -> AuthorizationContext:
    return AuthorizationContext(
        principal="test-user",
        roles=["admin"],
        permissions=["recovery.plan.execute"],
    )


@pytest.fixture
def sample_plan() -> RecoveryPlan:
    return RecoveryPlan(
        plan_id="plan-123",
        incident_id="inc-1",
        overall_risk="LOW",
        impact_analysis="None",
        steps=[
            RecoveryStep(
                action_type=RecoveryActionType.SCALE_UP,
                target_component="service-a",
                justification="Testing execution",
                estimated_risk="LOW",
            )
        ],
    )


@pytest.fixture
def sample_approval(sample_plan: RecoveryPlan) -> ApprovalRequestResponse:
    plan_hash = PlanIntegrity.compute_hash(sample_plan)
    return ApprovalRequestResponse(
        approval_id="app-123",
        plan_id=sample_plan.plan_id,
        plan_hash=plan_hash,
        status=ApprovalStatus.APPROVED,
        requested_by="other-user",
        requested_at=datetime.now(UTC) - timedelta(minutes=5),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )


@pytest.fixture
def execution_gate() -> ExecutionGate:
    return ExecutionGate()


@pytest.fixture
def execution_engine(execution_gate: ExecutionGate) -> ExecutionEngine:
    return ExecutionEngine(gate=execution_gate, timeout_seconds=2.0)


# ---------------------------------------------------------------------------
# AUTHORIZATION AND INTEGRITY TESTS
# ---------------------------------------------------------------------------


def test_gate_rejects_pending_approval(execution_gate: ExecutionGate, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext):
    sample_approval.status = ApprovalStatus.PENDING
    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    with pytest.raises(AuthorizationError, match="must be APPROVED"):
        execution_gate.authorize(auth)


def test_gate_rejects_expired_approval(execution_gate: ExecutionGate, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext):
    sample_approval.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    with pytest.raises(AuthorizationError, match="expired"):
        execution_gate.authorize(auth)


def test_gate_rejects_tampered_plan(execution_gate: ExecutionGate, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext):
    sample_plan.steps[0].target_component = "malicious-target"
    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    with pytest.raises(IntegrityError, match="Plan hash mismatch"):
        execution_gate.authorize(auth)


def test_gate_rejects_unauthorized_principal(execution_gate: ExecutionGate, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse):
    auth_context = AuthorizationContext(principal="hacker", permissions=[])
    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    with pytest.raises(AuthorizationError, match=r"lacks 'recovery\.plan\.execute' permission"):
        execution_gate.authorize(auth)


def test_gate_allows_valid_authorization(execution_gate: ExecutionGate, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext):
    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    execution_gate.authorize(auth)  # Should not raise


# ---------------------------------------------------------------------------
# REGISTRY TESTS
# ---------------------------------------------------------------------------


def test_registry_rejects_unknown_action():
    with pytest.raises(ValueError, match="Unsupported action type"):
        ExecutorRegistry.get_executor("UNKNOWN")


# ---------------------------------------------------------------------------
# ENGINE EXECUTION TESTS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_executes_successfully(execution_engine: ExecutionEngine, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext):
    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    results = await execution_engine.execute(auth)
    assert len(results) == 1
    assert results[0].status == ExecutionStatus.SUCCESS
    assert results[0].action_type == RecoveryActionType.SCALE_UP
    assert results[0].executor_type == "SimulatedScaleUpExecutor"


@pytest.mark.asyncio
async def test_engine_handles_timeout(execution_gate: ExecutionGate, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext, monkeypatch: pytest.MonkeyPatch):
    # Create an engine with a very short timeout
    fast_timeout_engine = ExecutionEngine(gate=execution_gate, timeout_seconds=0.1)

    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    results = await fast_timeout_engine.execute(auth)

    assert len(results) == 1
    assert results[0].status == ExecutionStatus.TIMEOUT
    assert "exceeded timeout" in results[0].error_message


@pytest.mark.asyncio
async def test_engine_handles_adapter_exception(execution_engine: ExecutionEngine, sample_plan: RecoveryPlan, sample_approval: ApprovalRequestResponse, auth_context: AuthorizationContext, monkeypatch: pytest.MonkeyPatch):
    class FailingExecutor(ExecutionAdapter):
        async def execute(self, target: str) -> bool:
            raise RuntimeError("Internal infra failure")

    # Monkeypatch the registry just for this test
    monkeypatch.setitem(ExecutorRegistry._registry, RecoveryActionType.SCALE_UP, FailingExecutor())

    auth = ExecutionAuthorization(plan=sample_plan, approval=sample_approval, auth_context=auth_context)
    results = await execution_engine.execute(auth)

    assert len(results) == 1
    assert results[0].status == ExecutionStatus.FAILED
    assert results[0].error_category == "RuntimeError"
    assert "Internal infra failure" in results[0].error_message
