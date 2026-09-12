from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.execution.models import ExecutionResult
from backend.intelligence.feedback.models import Feedback, LearningSignal
from backend.intelligence.memory.models import Experience, RetrievalQuery, RetrievalResult
from backend.intelligence.outcomes.models import OutcomeAssessment

router = APIRouter(tags=["Memory"])

# Mock stores for Phase 13 v0 API demonstration
_MOCK_EXPERIENCE_STORE: dict[str, Experience] = {}
_MOCK_RETRIEVAL_STORE: dict[str, RetrievalResult] = {}


@router.post(
    "/intelligence/memory/experiences",
    response_model=dict,
    summary="Create a historical episodic experience from a lineage of artifacts",
)
async def create_experience(
    request: Request,
    execution: ExecutionResult,
    assessment: OutcomeAssessment,
    feedback: Feedback,
    signal: LearningSignal,
    incident_id: str | None = None,
    environment: str | None = None,
) -> dict:
    """
    Creates an Experience representing a historical episode.
    Idempotent: Enforced on learning_signal_id.
    """

    # 1. Idempotency Check
    existing_exp = next((e for e in _MOCK_EXPERIENCE_STORE.values() if e.learning_signal_id == signal.signal_id), None)
    if existing_exp:
        return {
            "experience": existing_exp,
            "status": "EXISTING_RECORD_RETURNED",
        }

    # 2. Generate
    engine = request.app.state.experience_engine
    try:
        experience = engine.build_experience(
            execution=execution,
            assessment=assessment,
            feedback=feedback,
            signal=signal,
            incident_id=incident_id,
            environment=environment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 3. Store
    _MOCK_EXPERIENCE_STORE[experience.experience_id] = experience

    return {
        "experience": experience,
        "status": "GENERATED_NEW_RECORD",
    }


@router.get("/intelligence/memory/experiences/{experience_id}", response_model=Experience)
async def get_experience(experience_id: str) -> Experience:
    if experience_id not in _MOCK_EXPERIENCE_STORE:
        raise HTTPException(status_code=404, detail="Experience not found")
    return _MOCK_EXPERIENCE_STORE[experience_id]


@router.post(
    "/intelligence/memory/retrieve",
    response_model=RetrievalResult,
    summary="Retrieve historical experiences deterministically",
)
async def retrieve_experiences(
    request: Request,
    query: RetrievalQuery,
) -> RetrievalResult:
    """
    Retrieves historical episodes ranked by deterministic relevance to the query.
    """
    engine = request.app.state.retrieval_engine

    all_experiences = list(_MOCK_EXPERIENCE_STORE.values())
    result = engine.retrieve(query, all_experiences)

    _MOCK_RETRIEVAL_STORE[result.retrieval_id] = result
    return result


@router.get("/intelligence/memory/retrieval/{retrieval_id}", response_model=RetrievalResult)
async def get_retrieval(retrieval_id: str) -> RetrievalResult:
    if retrieval_id not in _MOCK_RETRIEVAL_STORE:
        raise HTTPException(status_code=404, detail="Retrieval result not found")
    return _MOCK_RETRIEVAL_STORE[retrieval_id]
