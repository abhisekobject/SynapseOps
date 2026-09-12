import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_session
from backend.events.models import Event
from backend.models.db.event import EventORM

router = APIRouter(prefix="/events", tags=["Operational Events"])


@router.get(
    "",
    response_model=dict,
    summary="Get operational events",
)
async def get_events(
    service_id: str | None = Query(None, description="Filter by service ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return operational events with pagination."""
    query = select(EventORM).order_by(EventORM.created_at.desc())

    if service_id:
        query = query.where(EventORM.service_id == service_id)
    if event_type:
        query = query.where(EventORM.event_type == event_type)

    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "items": [
            Event(
                id=e.id,
                event_type=e.event_type,
                service_id=e.service_id,
                severity=e.severity,
                status=e.status,
                message=e.message,
                correlation_id=e.correlation_id,
                trace_id=e.trace_id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                evidence=e.evidence or {},
            )
            for e in events
        ],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


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


@router.get(
    "/history",
    response_model=dict,
    summary="Get historical events",
)
async def get_event_history(
    service_id: str | None = Query(None, description="Filter by service ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return historical operational events with pagination."""
    query = select(EventORM).order_by(EventORM.created_at.desc())

    if service_id:
        query = query.where(EventORM.service_id == service_id)
    if event_type:
        query = query.where(EventORM.event_type == event_type)

    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "items": [
            Event(
                id=e.id,
                event_type=e.event_type,
                service_id=e.service_id,
                severity=e.severity,
                status=e.status,
                message=e.message,
                correlation_id=e.correlation_id,
                trace_id=e.trace_id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                evidence=e.evidence or {},
            )
            for e in events
        ],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.get(
    "/{event_id}",
    response_model=Event,
    summary="Get a specific event",
)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Event:
    """Return a specific operational event by ID."""
    try:
        parsed_id = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format") from None

    db_event = await db.get(EventORM, parsed_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return Event(
        id=db_event.id,
        event_type=db_event.event_type,
        service_id=db_event.service_id,
        severity=db_event.severity,
        status=db_event.status,
        message=db_event.message,
        correlation_id=db_event.correlation_id,
        trace_id=db_event.trace_id,
        created_at=db_event.created_at,
        updated_at=db_event.updated_at,
        evidence=db_event.evidence or {},
    )
