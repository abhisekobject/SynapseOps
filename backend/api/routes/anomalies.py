import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_session
from backend.models.db.anomaly import AnomalyORM
from backend.models.domain.anomaly import Anomaly

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get(
    "",
    response_model=dict,
    summary="Get anomalies",
)
async def get_anomalies(
    service_name: str | None = Query(None, description="Filter by service name"),
    status: str | None = Query(None, description="Filter by status"),
    incident_id: str | None = Query(None, description="Filter by incident ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return anomalies with pagination."""
    query = select(AnomalyORM).order_by(AnomalyORM.detected_at.desc())

    if service_name:
        query = query.where(AnomalyORM.service_name == service_name)
    if status:
        query = query.where(AnomalyORM.status == status)
    if incident_id:
        try:
            incident_uuid = uuid.UUID(incident_id)
            query = query.where(AnomalyORM.incident_id == incident_uuid)
        except ValueError:
            pass

    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    anomalies = result.scalars().all()

    return {
        "items": [
            Anomaly.model_validate(a)
            for a in anomalies
        ],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.get(
    "/{anomaly_id}",
    response_model=Anomaly,
    summary="Get a specific anomaly",
)
async def get_anomaly(
    anomaly_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Anomaly:
    """Return a specific anomaly by ID."""
    try:
        parsed_id = uuid.UUID(anomaly_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format") from None

    db_anomaly = await db.get(AnomalyORM, parsed_id)
    if not db_anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    return Anomaly.model_validate(db_anomaly)
