"""
SynapseOps Health API Routes.

Provides liveness and readiness endpoints.

Liveness (/health/live):
    Indicates whether the application process is running and responsive.
    Should not check external dependencies — only that the process itself is alive.
    Used by container orchestrators to know whether to restart the container.

Readiness (/health/ready):
    Indicates whether the application is ready to serve traffic.
    Checks that required external dependencies (PostgreSQL, Redis) are reachable.
    Used by load balancers to know whether to route traffic to this instance.

Combined (/health):
    Returns a summary suitable for quick human inspection during development.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.core.logging import get_logger

logger = get_logger("api.health")

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 if the process is alive. Does not check dependencies.",
    response_description="Process liveness status",
)
async def liveness() -> dict:
    """Liveness probe — process is running."""
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 if all required dependencies are reachable.",
    response_description="Dependency readiness status",
)
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe — checks PostgreSQL and Redis connectivity."""
    db_ok = False
    redis_ok = False
    details: dict[str, str] = {}

    # Check PostgreSQL
    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
        details["postgres"] = "ok"
    except Exception as exc:
        details["postgres"] = f"unavailable: {type(exc).__name__}"
        logger.warning("Readiness check: PostgreSQL unavailable", error=str(exc))

    # Check Redis
    try:
        from backend.cache.redis import check_redis_connectivity

        redis_client = request.app.state.redis_client
        redis_ok = await check_redis_connectivity(redis_client)
        details["redis"] = "ok" if redis_ok else "unavailable"
    except Exception as exc:
        details["redis"] = f"unavailable: {type(exc).__name__}"
        logger.warning("Readiness check: Redis unavailable", error=str(exc))

    all_ready = db_ok and redis_ok
    http_status = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if all_ready else "not_ready",
            "dependencies": details,
        },
    )


@router.get(
    "",
    summary="Health summary",
    description="Combined health summary for human inspection.",
    response_description="Application health summary",
)
async def health_summary(request: Request) -> JSONResponse:
    """Combined health summary — useful during development."""
    from backend.core.config import get_settings

    settings = get_settings()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "version": "0.1.0",
            "phase": "Phase 1 — Project Foundation",
        },
    )
