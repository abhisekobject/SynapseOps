"""
Phase 16 — Adaptive Decision Intelligence: API Routes.

Endpoints:
    POST /api/v1/intelligence/decision/analyze
    GET  /api/v1/intelligence/decision/{decision_id}

BOUNDARY:
    These endpoints are ANALYSIS-ONLY.
    They do NOT execute any actions.
    They do NOT authorize any actions.
    They do NOT modify Safety/Policy.
    They do NOT modify any Experience, Signal, or Knowledge records.
    They do NOT call any execution function.

The output of these endpoints is:
    - A ranked list of evidence-backed decision candidates
    - For consumption by the Operations Console (Phase 15 frontend)
    - For referral to the Safety/Policy pipeline (Phase 9)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.decision.engine import DecisionEngine
from backend.intelligence.decision.models import DecisionAnalysis, DecisionContext
from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    OperationalKnowledge,
)
from backend.intelligence.memory.models import Experience

router = APIRouter(prefix="/intelligence/decision", tags=["Decision Intelligence"])

# v0 in-memory store — mirrors Phase 13/14 pattern.
# Key: decision_id → DecisionAnalysis
# NOTE: decisions are re-analyzed on demand; this store provides idempotent
# retrieval of previous analyses. In a future phase this could be DB-backed.
_DECISION_STORE: dict[str, DecisionAnalysis] = {}

# Module-level engine (stateless — safe to reuse across requests)
_decision_engine = DecisionEngine()


@router.post(
    "/analyze",
    response_model=DecisionAnalysis,
    summary="Analyze incident evidence and produce adaptive decision candidates",
)
async def analyze_decision(
    request: Request,
    context: DecisionContext,
) -> DecisionAnalysis:
    """
    Performs a Phase 16 adaptive decision intelligence analysis.

    Given a DecisionContext (current incident evidence), retrieves:
      - Relevant historical experiences (Phase 13 Memory)
      - Learning signals (Phase 14)
      - Operational knowledge aggregates (Phase 14)

    Returns a DecisionAnalysis with ranked, explainable, evidence-backed candidates.

    SAFETY CONTRACT:
      - This endpoint NEVER executes any actions.
      - This endpoint NEVER bypasses Safety or Authorization.
      - Candidates must still pass the Safety/Policy pipeline before any
        execution can be authorized.

    IDEMPOTENCY:
      - Repeated analysis of the same context returns the stored result
        if one already exists for this decision_id.
      - Use POST to force a fresh analysis with the same context.
        (Note: since decision_id is deterministic, the result is the same.)
    """
    # Retrieve current historical evidence from Phase 13 and 14 in-memory stores.
    # We reach into the route module-level stores via app.state references.
    experiences = _get_experiences(request)
    learning_signals = _get_learning_signals(request)
    operational_knowledge = _get_operational_knowledge(request)

    # Perform decision analysis
    analysis = _decision_engine.analyze(
        context=context,
        experiences=experiences,
        learning_signals=learning_signals,
        operational_knowledge=operational_knowledge,
    )

    # Store result (idempotent upsert)
    _DECISION_STORE[analysis.decision_id] = analysis

    return analysis


@router.get(
    "/{decision_id}",
    response_model=DecisionAnalysis,
    summary="Retrieve a previous decision analysis by ID",
)
async def get_decision(decision_id: str) -> DecisionAnalysis:
    """
    Retrieve a previously stored decision analysis.

    Returns 404 if the decision_id has not been analyzed in this session.
    """
    if decision_id not in _DECISION_STORE:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Decision analysis '{decision_id}' not found. "
                "Use POST /analyze to create a new analysis."
            ),
        )
    return _DECISION_STORE[decision_id]


@router.get(
    "",
    response_model=list[DecisionAnalysis],
    summary="List all decision analyses",
)
async def list_decisions() -> list[DecisionAnalysis]:
    """
    Returns all stored decision analyses, ordered by generated_at descending.
    """
    return sorted(
        _DECISION_STORE.values(),
        key=lambda d: (d.generated_at, d.decision_id),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Internal helpers — fetch from Phase 13 and 14 in-memory stores
# ---------------------------------------------------------------------------

def _get_experiences(request: Request) -> list[Experience]:
    """Fetch all available experiences from the Phase 13 in-memory store."""
    try:
        # Phase 13 memory routes store experiences in a module-level dict.
        # We import the store reference to avoid duplicating state.
        from backend.api.routes.memory import _MOCK_EXPERIENCE_STORE
        return list(_MOCK_EXPERIENCE_STORE.values())
    except Exception:
        return []


def _get_learning_signals(request: Request) -> list[ExperienceLearningSignal]:
    """Fetch all available learning signals from the Phase 14 in-memory store."""
    try:
        from backend.api.routes.learning import _SIGNAL_STORE
        return list(_SIGNAL_STORE.values())
    except Exception:
        return []


def _get_operational_knowledge(request: Request) -> list[OperationalKnowledge]:
    """Fetch all available operational knowledge from the Phase 14 in-memory store."""
    try:
        from backend.api.routes.learning import _KNOWLEDGE_STORE
        return list(_KNOWLEDGE_STORE.values())
    except Exception:
        return []
