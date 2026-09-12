from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult

router = APIRouter(tags=["Intelligence"])


@router.get(
    "/intelligence/incident-reasoning",
    response_model=IncidentReasoningResult,
    summary="Generate AI incident reasoning",
)
async def get_incident_reasoning(
    request: Request,
    window_minutes: int = 15,
) -> IncidentReasoningResult:
    """Analyze recent active events and generate structured AI reasoning."""
    event_engine = request.app.state.event_engine
    state_engine = request.app.state.state_engine
    dependency_graph = request.app.state.dependency_graph
    rca_engine = request.app.state.rca_engine
    reasoning_provider = request.app.state.reasoning_provider

    # 1. Gather active events
    active_events = event_engine.get_all_active_events()

    # Filter to analysis window
    now = datetime.now(UTC)
    cutoff = now.timestamp() - (window_minutes * 60)
    recent_active_events = [
        e for e in active_events
        if e.created_at.timestamp() >= cutoff or e.updated_at.timestamp() >= cutoff
    ]

    # 2. Run deterministic RCA
    rca_result = rca_engine.analyze(recent_active_events, window_minutes=window_minutes)

    # 3. Get State Snapshot
    state_snapshot = await state_engine.get_system_snapshot()

    # 4. Extract topology
    # Just passing nodes and edges for context bounds
    nodes = dependency_graph.get_all_nodes()
    edges = []
    for node in nodes:
        for dep in dependency_graph.get_direct_dependencies(node):
            edges.append({"source": node, "target": dep})

    # 5. Build Incident Context
    context = IncidentContext(
        analysis_window_minutes=window_minutes,
        active_events=recent_active_events,
        rca_result=rca_result,
        system_state=state_snapshot,
        topology_nodes=nodes,
        topology_edges=edges,
    )

    # 6. Call AI Provider
    try:
        reasoning_result = await reasoning_provider.analyze(context)
        return reasoning_result
    except Exception as e:
        # Graceful degradation - AI failure does not break the API, but this endpoint fails.
        raise HTTPException(
            status_code=503,
            detail=f"AI Incident Reasoning unavailable: {e}"
        ) from e
