"""SynapseOps API Router — aggregates all route modules."""

from fastapi import APIRouter

from backend.api.routes.health import router as health_router
from backend.api.routes.simulation import router as simulation_router

# Root API router — all route modules are included here
api_router = APIRouter()
api_router.include_router(health_router)

# Phase 2: Simulation control API
api_router.include_router(simulation_router, prefix="/api/v1")
