from fastapi import APIRouter, Depends, HTTPException, Request

from backend.intelligence.execution.models import ExecutionAuthorization, ExecutionResult
from backend.intelligence.recovery.models import RecoveryPlan
from backend.intelligence.safety.models import ApprovalRequestResponse, AuthorizationContext

router = APIRouter(tags=["Execution"])


def get_auth_context(request: Request) -> AuthorizationContext:
    """Mock auth context for Phase 10 demonstration."""
    principal = request.headers.get("X-User-Id", "system")
    roles = request.headers.get("X-User-Roles", "user").split(",")
    permissions = request.headers.get("X-User-Permissions", "recovery.plan.execute").split(",")

    return AuthorizationContext(
        principal=principal,
        roles=roles,
        permissions=permissions,
    )


# Simulated stores for Phase 10 API verification
_MOCK_APPROVALS_STORE: dict[str, ApprovalRequestResponse] = {}
_MOCK_EXECUTION_RECORDS: list[ExecutionResult] = []


@router.post(
    "/intelligence/execution/execute",
    response_model=list[ExecutionResult],
    summary="Execute an authorized recovery plan",
)
async def execute_plan(
    request: Request,
    approval_id: str,
    plan: RecoveryPlan,
    auth: AuthorizationContext = Depends(get_auth_context),
) -> list[ExecutionResult]:
    """
    Executes an authorized plan.
    Requires the original plan object and the approval_id.
    """
    engine = request.app.state.execution_engine

    # Check Idempotency (has this approval already been executed?)
    # In a real app, query `ExecutionRecordORM` by `approval_id`
    for record in _MOCK_EXECUTION_RECORDS:
        if record.approval_id == approval_id:
            raise HTTPException(status_code=409, detail="Duplicate execution: this approval ID has already been processed.")

    # Fetch Approval
    approval = _MOCK_APPROVALS_STORE.get(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    auth_req = ExecutionAuthorization(
        plan=plan,
        approval=approval,
        auth_context=auth,
    )

    # ExecutionEngine handles the strict authorization gate
    results = await engine.execute(auth_req)

    # Store results
    _MOCK_EXECUTION_RECORDS.extend(results)

    # In a real system, persist these results to ExecutionRecordORM

    return results
