"""
SynapseOps Simulation API Routes.

Provides the REST interface for controlling the simulated infrastructure:
- Inject failures (named scenarios or custom)
- Clear active failures
- Query simulation state
- List pre-defined scenarios
- Get health snapshots from all simulated services

All routes are prefixed with /api/v1/simulation (registered in router.py).

Design:
- The FailureController is retrieved from request.app.state.failure_controller.
- If the failure controller is not initialised (e.g. in tests that don't
  set up the full lifecycle), a 503 is returned.
- Service health polling uses an async HTTP client (httpx) to fetch
  /health from each simulated service. Connection failures are handled
  gracefully — the snapshot reflects the service as unreachable.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.simulation.models import (
    ClearFailuresRequest,
    ClearFailuresResponse,
    InjectFailureRequest,
    InjectFailureResponse,
    SimulationState,
)
from backend.simulation.scenarios import (
    SCENARIO_REGISTRY,
    build_scenario_request,
    get_scenario_names,
)

logger = get_logger("api.simulation")
router = APIRouter(prefix="/simulation", tags=["Simulation"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_controller(request: Request):
    """Retrieve the FailureController from app state.

    Raises:
        HTTPException 503: If the failure controller is not initialised.
    """
    controller = getattr(request.app.state, "failure_controller", None)
    if controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Simulation controller is not initialised.",
        )
    return controller


# ---------------------------------------------------------------------------
# Failure injection routes
# ---------------------------------------------------------------------------


@router.post(
    "/failures/inject",
    response_model=InjectFailureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inject a failure scenario",
    description=(
        "Inject a failure into the simulated infrastructure. "
        "Provide either `scenario_name` to use a pre-defined scenario, "
        "or explicit `failure_type`, `target`, and `severity` for a custom failure."
    ),
)
async def inject_failure(
    request: Request,
    body: InjectFailureRequest,
) -> InjectFailureResponse:
    """Inject a failure scenario into the simulated infrastructure."""
    controller = _get_controller(request)

    # If scenario_name is provided, merge with pre-defined scenario defaults
    if body.scenario_name:
        if body.scenario_name not in SCENARIO_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unknown scenario name '{body.scenario_name}'. "
                    f"Available: {get_scenario_names()}"
                ),
            )
        # Build the named scenario and overlay any custom fields from the request
        named = build_scenario_request(body.scenario_name)
        resolved = named.model_copy(
            update={
                k: v
                for k, v in body.model_dump(exclude_unset=True, exclude={"scenario_name"}).items()
                if v is not None
            }
        )
    else:
        # Custom failure — validate required fields
        if body.failure_type is None or body.target is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Custom failure injection requires `failure_type` and `target`. "
                    "Alternatively, provide `scenario_name` to use a pre-defined scenario."
                ),
            )
        resolved = body

    result = await controller.inject_failure(resolved)
    logger.info(
        "Failure injection requested via API",
        scenario_id=str(result.scenario.id),
        name=result.scenario.name,
        target=result.scenario.target,
        failure_type=result.scenario.failure_type,
    )
    return result


# ---------------------------------------------------------------------------
# Clear failures
# ---------------------------------------------------------------------------


@router.delete(
    "/failures",
    response_model=ClearFailuresResponse,
    summary="Clear active failures",
    description=(
        "Clear active failure scenarios. "
        "If `target` is specified, only clears failures for that target. "
        "Otherwise, clears all active failures."
    ),
)
async def clear_failures(
    request: Request,
    body: ClearFailuresRequest | None = None,
) -> ClearFailuresResponse:
    """Clear all (or targeted) active failure scenarios."""
    controller = _get_controller(request)
    clear_request = body or ClearFailuresRequest()
    result = await controller.clear_failures(clear_request)
    logger.info(
        "Failures cleared via API",
        cleared_count=result.cleared_count,
        target=str(clear_request.target),
    )
    return result


# ---------------------------------------------------------------------------
# Simulation state query
# ---------------------------------------------------------------------------


@router.get(
    "/state",
    response_model=SimulationState,
    summary="Get current simulation state",
    description="Returns a snapshot of all currently active failure scenarios.",
)
async def get_simulation_state(request: Request) -> SimulationState:
    """Return the current simulation state."""
    controller = _get_controller(request)
    return await controller.get_state()


# ---------------------------------------------------------------------------
# Pre-defined scenario catalogue
# ---------------------------------------------------------------------------


@router.get(
    "/scenarios",
    summary="List pre-defined failure scenarios",
    description="Returns the catalogue of all available named failure scenarios.",
)
async def list_scenarios() -> JSONResponse:
    """List all pre-defined named scenarios with their configurations."""
    scenarios = []
    for name in get_scenario_names():
        req = build_scenario_request(name)
        scenarios.append(
            {
                "name": name,
                "failure_type": req.failure_type,
                "target": req.target,
                "severity": req.severity,
                "duration_seconds": req.duration_seconds,
                "description": req.description,
            }
        )
    return JSONResponse(
        content={
            "scenarios": scenarios,
            "total": len(scenarios),
        }
    )


@router.post(
    "/scenarios/{name}/activate",
    response_model=InjectFailureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activate a named scenario",
    description=(
        "Activate a pre-defined failure scenario by name. "
        "Equivalent to POST /failures/inject with scenario_name set."
    ),
)
async def activate_scenario(
    name: str,
    request: Request,
) -> InjectFailureResponse:
    """Activate a pre-defined named failure scenario."""
    if name not in SCENARIO_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{name}' not found. Available: {get_scenario_names()}",
        )
    controller = _get_controller(request)
    scenario_request = build_scenario_request(name)
    result = await controller.inject_failure(scenario_request)
    logger.info("Named scenario activated via API", name=name, scenario_id=str(result.scenario.id))
    return result


# ---------------------------------------------------------------------------
# Simulated service health aggregation
# ---------------------------------------------------------------------------


@router.get(
    "/services/health",
    summary="Get health snapshots from all simulated services",
    description=(
        "Polls /health on each simulated service and returns aggregated snapshots. "
        "Unreachable services are reported with status 'unreachable'."
    ),
)
async def get_services_health(request: Request) -> JSONResponse:
    """Poll all simulated services for their health snapshots."""
    settings = get_settings()

    service_urls = {
        "sim-gateway": settings.sim_gateway_url,
        "sim-api": settings.sim_api_url,
        "sim-worker": settings.sim_worker_url,
    }

    snapshots = {}

    async with httpx.AsyncClient(timeout=3.0) as client:
        for svc_name, base_url in service_urls.items():
            try:
                response = await client.get(f"{base_url}/health")
                response.raise_for_status()
                snapshots[svc_name] = response.json()
            except httpx.ConnectError:
                snapshots[svc_name] = {
                    "service_name": svc_name,
                    "status": "unreachable",
                    "detail": "Connection refused — service may not be running.",
                }
            except httpx.TimeoutException:
                snapshots[svc_name] = {
                    "service_name": svc_name,
                    "status": "unreachable",
                    "detail": "Health check timed out.",
                }
            except Exception as exc:
                snapshots[svc_name] = {
                    "service_name": svc_name,
                    "status": "error",
                    "detail": f"{type(exc).__name__}: {exc}",
                }

    healthy_count = sum(1 for s in snapshots.values() if s.get("status") == "healthy")

    return JSONResponse(
        content={
            "services": snapshots,
            "total_services": len(snapshots),
            "healthy_count": healthy_count,
        }
    )
