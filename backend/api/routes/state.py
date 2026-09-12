import math

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_session
from backend.models.db.state import StateTransitionORM
from backend.state.models import StateTransition, SystemSnapshot

router = APIRouter(prefix="/state", tags=["System State"])


@router.get(
    "",
    response_model=SystemSnapshot,
    summary="Get current system state snapshot",
)
async def get_system_state(request: Request) -> SystemSnapshot:
    """Return a coherent snapshot of the entire infrastructure system state."""
    state_engine = request.app.state.state_engine
    return await state_engine.get_system_snapshot()


@router.get(
    "/services",
    response_model=list[dict],
    summary="Get status of all services",
)
async def get_services(request: Request) -> list[dict]:
    """Return the status of all known services."""
    state_engine = request.app.state.state_engine
    snapshot = await state_engine.get_system_snapshot()
    return [
        {"service_id": svc.service_id, "status": svc.status}
        for svc in snapshot.services.values()
    ]


@router.get(
    "/services/{service_id}",
    response_model=dict,
    summary="Get status of a specific service",
)
async def get_service(request: Request, service_id: str) -> dict:
    """Return the status of a specific service."""
    from fastapi import HTTPException
    state_engine = request.app.state.state_engine
    snapshot = await state_engine.get_system_snapshot()
    if service_id not in snapshot.services:
        raise HTTPException(status_code=404, detail="Service not found")
    svc = snapshot.services[service_id]
    return {"service_id": svc.service_id, "status": svc.status}


@router.get(
    "/history",
    response_model=dict,
    summary="Get historical state transitions",
)
async def get_state_history(
    service_id: str | None = Query(None, description="Filter by service ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return historical state transitions with pagination."""
    query = select(StateTransitionORM).order_by(StateTransitionORM.created_at.desc())

    if service_id:
        query = query.where(StateTransitionORM.service_id == service_id)

    # Count total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    transitions = result.scalars().all()

    return {
        "items": [
            StateTransition(
                id=str(t.id),
                service_id=t.service_id,
                previous_status=t.previous_status,
                new_status=t.new_status,
                reason=t.reason,
                created_at=t.created_at,
            )
            for t in transitions
        ],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }
