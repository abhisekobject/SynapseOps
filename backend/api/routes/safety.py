import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.intelligence.recovery.models import RecoveryPlan
from backend.intelligence.safety.models import (
    ApprovalRequestResponse,
    ApprovalStatus,
    AuthorizationContext,
    PlanIntegrity,
    PolicyDecision,
)

router = APIRouter(tags=["Safety"])


def get_auth_context(request: Request) -> AuthorizationContext:
    """Mock auth context for Phase 9 demonstration.
    In a real system, this would extract JWT claims or session data.
    """
    principal = request.headers.get("X-User-Id", "system")
    roles = request.headers.get("X-User-Roles", "user").split(",")
    permissions = request.headers.get("X-User-Permissions", "recovery.plan.view").split(",")

    return AuthorizationContext(
        principal=principal,
        roles=roles,
        permissions=permissions,
    )


@router.post(
    "/intelligence/safety/policy/evaluate",
    response_model=PolicyDecision,
    summary="Evaluate a RecoveryPlan against the deterministic policy engine",
)
async def evaluate_policy(
    request: Request,
    plan: RecoveryPlan,
    auth: AuthorizationContext = Depends(get_auth_context),
) -> PolicyDecision:
    """Evaluates the plan and returns ALLOW, DENY, or REQUIRES_APPROVAL."""
    policy_engine = request.app.state.policy_engine
    plan_hash = PlanIntegrity.compute_hash(plan)

    decision = policy_engine.evaluate(plan, plan_hash)
    decision.decision_id = str(uuid.uuid4())

    # In a real system, we would persist this decision to PolicyDecisionORM via SQLAlchemy session here.
    return decision


@router.post(
    "/intelligence/safety/approvals",
    response_model=ApprovalRequestResponse,
    summary="Request human approval for a RecoveryPlan",
)
async def request_approval(
    request: Request,
    plan: RecoveryPlan,
    auth: AuthorizationContext = Depends(get_auth_context),
) -> ApprovalRequestResponse:
    """Creates a PENDING approval request."""
    if "recovery.plan.request_approval" not in auth.permissions:
        raise HTTPException(status_code=403, detail="Lacking recovery.plan.request_approval permission")

    plan_hash = PlanIntegrity.compute_hash(plan)

    approval = ApprovalRequestResponse(
        approval_id=str(uuid.uuid4()),
        plan_id=plan.plan_id,
        plan_hash=plan_hash,
        status=ApprovalStatus.PENDING,
        requested_by=auth.principal,
        requested_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    # In a real system, persist this to ApprovalRequestORM here

    return approval


# For tests, we use an in-memory mock store for approvals to test state transitions easily.
_MOCK_APPROVALS_STORE: dict[str, ApprovalRequestResponse] = {}

@router.post(
    "/intelligence/safety/approvals/{approval_id}/approve",
    response_model=ApprovalRequestResponse,
)
async def approve_plan(
    request: Request,
    approval_id: str,
    plan: RecoveryPlan,
    auth: AuthorizationContext = Depends(get_auth_context),
) -> ApprovalRequestResponse:
    """Grants human approval, enforcing separation of duties."""
    approval_engine = request.app.state.approval_engine

    # Simulate DB fetch
    approval = _MOCK_APPROVALS_STORE.get(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    plan_hash = PlanIntegrity.compute_hash(plan)

    try:
        updated_approval = approval_engine.approve(approval, auth, plan_hash)
        _MOCK_APPROVALS_STORE[approval_id] = updated_approval
        return updated_approval
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
