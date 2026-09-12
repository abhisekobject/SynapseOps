from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult
from backend.intelligence.recovery.models import RecoveryPlan

router = APIRouter(tags=["Intelligence"])


@router.post(
    "/intelligence/recovery-plan",
    response_model=RecoveryPlan,
    summary="Generate a validated recovery plan from incident reasoning",
)
async def create_recovery_plan(
    request: Request,
    reasoning: IncidentReasoningResult,
) -> RecoveryPlan:
    """Consume Phase 7 reasoning and generate a bounded Phase 8 recovery plan."""
    recovery_planner = request.app.state.recovery_planner
    plan_validator = request.app.state.plan_validator
    dependency_graph = request.app.state.dependency_graph

    # Reconstruct the bare minimum context needed for validation (topology)
    nodes = dependency_graph.get_all_nodes()

    # We construct a mock IncidentContext here purely for validation bounds.
    # In a full flow, we might pass the full context from Phase 7.
    context = IncidentContext(
        analysis_window_minutes=0,
        active_events=[],
        rca_result=None,
        system_state=None,
        topology_nodes=nodes,
        topology_edges=[],
    )

    try:
        raw_plan = await recovery_planner.generate_plan(reasoning, context)
        validated_plan = plan_validator.validate(raw_plan, context)
        return validated_plan
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Recovery Planning unavailable: {e}"
        ) from e
