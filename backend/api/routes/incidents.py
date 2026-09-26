import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_session
from backend.models.db.incident import IncidentORM
from backend.models.domain.incident import Incident

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=dict,
    summary="Get incidents",
)
async def get_incidents(
    status: str | None = Query(None, description="Filter by status"),
    severity: str | None = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return incidents with pagination."""
    query = select(IncidentORM).order_by(IncidentORM.detected_at.desc())

    if status:
        query = query.where(IncidentORM.status == status)
    if severity:
        query = query.where(IncidentORM.severity == severity)

    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    incidents = result.scalars().all()

    return {
        "items": [
            Incident.model_validate(i)
            for i in incidents
        ],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.get(
    "/{incident_id}",
    response_model=Incident,
    summary="Get a specific incident",
)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Incident:
    """Return a specific incident by ID."""
    try:
        parsed_id = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format") from None

    db_incident = await db.get(IncidentORM, parsed_id)
    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return Incident.model_validate(db_incident)
