from fastapi import APIRouter, Request

from backend.state.models import SystemSnapshot

router = APIRouter(prefix="/state", tags=["System State"])


@router.get(
    "",
    response_model=SystemSnapshot,
    summary="Get current system state snapshot",
)
async def get_system_state(request: Request) -> SystemSnapshot:
    """Return a coherent snapshot of the entire infrastructure system state."""
    state_engine = request.app.state.state_engine
    return state_engine.get_system_snapshot()
