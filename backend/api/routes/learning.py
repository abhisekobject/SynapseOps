"""
Phase 14 — Operational Learning: API Routes.

Endpoints:
    POST /api/v1/intelligence/learning/signals/generate
    GET  /api/v1/intelligence/learning/signals
    GET  /api/v1/intelligence/learning/signals/{signal_id}
    POST /api/v1/intelligence/learning/aggregate
    GET  /api/v1/intelligence/learning/knowledge
    GET  /api/v1/intelligence/learning/knowledge/{knowledge_id}

BOUNDARY:
    All endpoints are READ-ONLY or EVIDENCE-GENERATION only.
    No endpoint modifies system behavior, authorizes actions,
    executes infrastructure commands, or modifies policies.
    No endpoint modifies model parameters.
"""

from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.learning.models import (
    ExperienceLearningSignal,
    KnowledgeAggregationQuery,
    OperationalKnowledge,
)
from backend.intelligence.memory.models import Experience

router = APIRouter(tags=["Learning"])

# v0 in-memory stores (mirrors Phase 13 architecture)
# Key for signals: signal_id
# Key for knowledge: knowledge_id
_SIGNAL_STORE: dict[str, ExperienceLearningSignal] = {}
_KNOWLEDGE_STORE: dict[str, OperationalKnowledge] = {}

# Idempotency index: experience_id → signal_id
_EXPERIENCE_SIGNAL_INDEX: dict[str, str] = {}


@router.post(
    "/intelligence/learning/signals/generate",
    response_model=dict,
    summary="Derive a structured learning signal from an episodic Experience",
)
async def generate_signal(
    request: Request,
    experience: Experience,
) -> dict:
    """
    Derives an ExperienceLearningSignal from a Phase 13 Experience.

    Idempotent: Repeated generation from the same experience returns the
    existing signal without creating a duplicate.

    BOUNDARY: This endpoint only reads the Experience and derives evidence.
    It does NOT modify system behavior, policies, or execution parameters.
    """
    # Idempotency check — one Experience → one Signal
    if experience.experience_id in _EXPERIENCE_SIGNAL_INDEX:
        existing_signal_id = _EXPERIENCE_SIGNAL_INDEX[experience.experience_id]
        return {
            "signal": _SIGNAL_STORE[existing_signal_id],
            "status": "EXISTING_SIGNAL_RETURNED",
        }

    engine = request.app.state.learning_engine
    try:
        signal = engine.generate_signal(experience)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Store
    _SIGNAL_STORE[signal.signal_id] = signal
    _EXPERIENCE_SIGNAL_INDEX[experience.experience_id] = signal.signal_id

    return {
        "signal": signal,
        "status": "GENERATED_NEW_SIGNAL",
    }


@router.get(
    "/intelligence/learning/signals",
    response_model=list[ExperienceLearningSignal],
    summary="List all learning signals",
)
async def list_signals(
    environment: str | None = None,
    is_simulated: bool | None = None,
    target_component: str | None = None,
    action_type: str | None = None,
) -> list[ExperienceLearningSignal]:
    """
    Returns all currently stored learning signals, with optional filtering.
    """
    signals = list(_SIGNAL_STORE.values())
    if environment is not None:
        signals = [s for s in signals if s.environment == environment]
    if is_simulated is not None:
        signals = [s for s in signals if s.is_simulated == is_simulated]
    if target_component is not None:
        signals = [s for s in signals if s.target_component == target_component]
    if action_type is not None:
        signals = [s for s in signals if s.action_type == action_type]
    # Deterministic ordering
    return sorted(signals, key=lambda s: (s.created_at, s.signal_id))


@router.get(
    "/intelligence/learning/signals/{signal_id}",
    response_model=ExperienceLearningSignal,
    summary="Retrieve a specific learning signal by ID",
)
async def get_signal(signal_id: str) -> ExperienceLearningSignal:
    """Return a specific ExperienceLearningSignal by signal_id."""
    if signal_id not in _SIGNAL_STORE:
        raise HTTPException(status_code=404, detail="Learning signal not found")
    return _SIGNAL_STORE[signal_id]


@router.post(
    "/intelligence/learning/aggregate",
    response_model=dict,
    summary="Aggregate learning signals into operational knowledge",
)
async def aggregate_knowledge(
    request: Request,
    query: KnowledgeAggregationQuery,
) -> dict:
    """
    Aggregates stored ExperienceLearningSignals matching the query dimensions
    into an OperationalKnowledge record.

    Environment Isolation:
        - is_simulated=True → aggregates only simulated signals
        - is_simulated=False → aggregates only production signals
        - is_simulated=None → all signals (explicitly mixed — labeled in knowledge_id)

    Idempotent: Repeated calls with the same query dimensions return the
    same knowledge_id (knowledge is deterministically re-generated).

    BOUNDARY: Knowledge is HISTORICAL EVIDENCE ONLY.
    It does NOT authorize, execute, or trigger any behavioral change.
    """
    aggregator = request.app.state.knowledge_aggregator

    all_signals = list(_SIGNAL_STORE.values())
    knowledge = aggregator.aggregate(all_signals, query)

    # Upsert (deterministic knowledge_id for given dimensions)
    _KNOWLEDGE_STORE[knowledge.knowledge_id] = knowledge

    return {
        "knowledge": knowledge,
        "status": "AGGREGATED",
    }


@router.get(
    "/intelligence/learning/knowledge",
    response_model=list[OperationalKnowledge],
    summary="List all operational knowledge records",
)
async def list_knowledge() -> list[OperationalKnowledge]:
    """Returns all stored OperationalKnowledge records."""
    return sorted(
        _KNOWLEDGE_STORE.values(),
        key=lambda k: (k.generated_at, k.knowledge_id),
    )


@router.get(
    "/intelligence/learning/knowledge/{knowledge_id}",
    response_model=OperationalKnowledge,
    summary="Retrieve a specific operational knowledge record",
)
async def get_knowledge(knowledge_id: str) -> OperationalKnowledge:
    """Return a specific OperationalKnowledge record by knowledge_id."""
    if knowledge_id not in _KNOWLEDGE_STORE:
        raise HTTPException(status_code=404, detail="Operational knowledge not found")
    return _KNOWLEDGE_STORE[knowledge_id]
