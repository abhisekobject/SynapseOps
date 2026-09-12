from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.models import RCAResult

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/dependencies", summary="Get complete dependency topology")
async def get_dependencies(request: Request) -> dict:
    """Returns the static topology of the simulated infrastructure."""
    graph = request.app.state.dependency_graph
    return graph.to_dict()


@router.get("/dependencies/{service_id}", summary="Get dependencies for a service")
async def get_service_dependencies(request: Request, service_id: str) -> dict:
    """Returns the direct and transitive dependencies and dependents for a specific service."""
    graph = request.app.state.dependency_graph
    if service_id not in graph.get_all_nodes():
        raise HTTPException(status_code=404, detail="Service not found in dependency graph")

    return {
        "service_id": service_id,
        "direct_dependencies": graph.get_direct_dependencies(service_id),
        "transitive_dependencies": graph.get_transitive_dependencies(service_id),
        "direct_dependents": graph.get_direct_dependents(service_id),
        "transitive_dependents": graph.get_transitive_dependents(service_id),
    }


@router.get("/rca/analyze", summary="Perform Root Cause Analysis", response_model=RCAResult)
async def analyze_root_cause(request: Request, window_minutes: int = 5) -> RCAResult:
    """Evaluates recent events and anomalies to produce ranked root-cause candidates."""
    event_engine = request.app.state.event_engine
    rca_engine = request.app.state.rca_engine

    active_events = event_engine.get_all_active_events()
    result = rca_engine.analyze(active_events=active_events, window_minutes=window_minutes)

    return result
