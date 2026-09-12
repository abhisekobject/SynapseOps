"""
SynapseOps Backend — Application Entry Point.

This module creates the FastAPI application, configures it, and defines
the application lifecycle (startup / shutdown).

Design notes:
- All configuration is sourced from environment variables via Pydantic Settings.
- Startup hooks initialize DB engine, session factory, and Redis client.
- Shutdown hooks close DB connections and Redis gracefully.
- Route modules are registered via the central API router.
- Exception handlers are registered to prevent internal error leakage.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router import api_router
from backend.cache.redis import close_redis_client, create_redis_client
from backend.core.config import get_settings
from backend.core.errors import register_exception_handlers
from backend.core.logging import configure_logging, get_logger
from backend.db.engine import create_engine
from backend.db.session import create_session_factory
from backend.observability.middleware import RequestCorrelationMiddleware
from backend.observability.tracing import configure_tracing, shutdown_tracing
from backend.simulation.controller import FailureController

settings = get_settings()

# Configure logging before anything else
configure_logging(
    log_level=settings.log_level,
    json_logs=(settings.environment == "production"),
)

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    On startup:
        - Creates the async database engine
        - Creates the session factory
        - Creates the Redis client

    On shutdown:
        - Disposes the database engine (closes all connections)
        - Closes the Redis client
    """
    logger.info(
        "SynapseOps starting",
        environment=settings.environment,
        phase="Phase 4 — System State & Event Intelligence",
    )

    # --- Startup ---
    # Phase 3: Initialise OpenTelemetry tracing before serving requests
    configure_tracing(settings)

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    redis_client = create_redis_client(settings)

    # Phase 2: Failure controller for the simulation layer
    failure_controller = FailureController.create(
        redis_client=redis_client,
        redis_failure_key=settings.sim_failure_redis_key,
    )
    failure_controller.start_expiry_task()

    # Phase 4: System State & Event Intelligence
    from backend.events.engine import EventEngine
    from backend.events.normalizer import TelemetryNormalizer
    from backend.state.engine import SystemStateEngine
    from backend.telemetry.ingestion import TelemetryPoller

    telemetry_normalizer = TelemetryNormalizer(settings)
    event_engine = EventEngine()
    state_engine = SystemStateEngine(settings)

    telemetry_poller = TelemetryPoller(
        settings=settings,
        normalizer=telemetry_normalizer,
        event_engine=event_engine,
        state_engine=state_engine,
    )
    telemetry_poller.start()

    # Attach to app.state so routes can access them via request.app.state
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis_client = redis_client
    app.state.failure_controller = failure_controller

    app.state.event_engine = event_engine
    app.state.state_engine = state_engine

    logger.info("SynapseOps startup complete")

    yield  # Application is running

    # --- Shutdown ---
    logger.info("SynapseOps shutting down")
    await telemetry_poller.stop()
    await failure_controller.stop()
    shutdown_tracing()
    await engine.dispose()
    await close_redis_client(redis_client)
    logger.info("SynapseOps shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Autonomous Infrastructure Intelligence & Self-Healing System — "
            "Experimental AIOps platform."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Phase 3: Request correlation ID + Prometheus metrics recording
    app.add_middleware(RequestCorrelationMiddleware)

    # Register all API routes
    app.include_router(api_router)

    return app


# Application instance (used by uvicorn and tests)
app = create_app()
