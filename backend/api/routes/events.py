from fastapi import APIRouter, Query, Request

from backend.events.models import Event

router = APIRouter(prefix="/events", tags=["Operational Events"])


@router.get(
    "/active",
    response_model=list[Event],
    summary="Get all active operational events",
)
async def get_active_events(
    request: Request,
    service_id: str | None = Query(None, description="Filter by service_id"),
) -> list[Event]:
    """Return all currently active events, optionally filtered by service."""
    event_engine = request.app.state.event_engine
    active = event_engine.get_all_active_events()

    if service_id:
        active = [e for e in active if e.service_id == service_id]

    return active
