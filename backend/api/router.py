"""SynapseOps API Router -- aggregates all route modules."""

from fastapi import APIRouter

from backend.api.routes.events import router as events_router
from backend.api.routes.execution import router as execution_router
from backend.api.routes.feedback import router as feedback_router
from backend.api.routes.health import router as health_router
from backend.api.routes.intelligence import router as intelligence_router
from backend.api.routes.learning import router as learning_router
from backend.api.routes.memory import router as memory_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.outcomes import router as outcomes_router
from backend.api.routes.reasoning import router as reasoning_router
from backend.api.routes.recovery import router as recovery_router
from backend.api.routes.safety import router as safety_router
from backend.api.routes.simulation import router as simulation_router
from backend.api.routes.state import router as state_router

# Root API router -- all route modules are included here
api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(metrics_router)  # Phase 3: /metrics

# Phase 2: Simulation control API
api_router.include_router(simulation_router, prefix="/api/v1")

# Phase 4: State and Events API
api_router.include_router(state_router, prefix="/api/v1")
api_router.include_router(events_router, prefix="/api/v1")

# Phase 6-14: Intelligence, AI, Recovery, Safety, Execution, Outcomes, Feedback, Memory & Learning API
api_router.include_router(intelligence_router, prefix="/api/v1")
api_router.include_router(reasoning_router, prefix="/api/v1")
api_router.include_router(recovery_router, prefix="/api/v1")
api_router.include_router(safety_router, prefix="/api/v1")
api_router.include_router(execution_router, prefix="/api/v1")
api_router.include_router(outcomes_router, prefix="/api/v1")
api_router.include_router(feedback_router, prefix="/api/v1")
api_router.include_router(memory_router, prefix="/api/v1")
api_router.include_router(learning_router, prefix="/api/v1")
