from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.execution.models import ExecutionResult
from backend.intelligence.outcomes.models import Observation, OutcomeAssessment

if TYPE_CHECKING:
    from backend.intelligence.outcomes.verification import VerificationEngine

router = APIRouter(tags=["Outcomes"])

# Mock stores for Phase 11 v0 API demonstration
_MOCK_EXECUTION_STORE: dict[str, ExecutionResult] = {}
_MOCK_OBSERVATION_STORE: list[Observation] = []
_MOCK_ASSESSMENT_STORE: list[OutcomeAssessment] = []


@router.post(
    "/intelligence/outcomes/observe",
    response_model=Observation,
    summary="Record an observation for a specific execution",
)
async def record_observation(
    request: Request,
    observation: Observation,
) -> Observation:
    """
    Records a deterministic observation of the system state.
    Requires a valid execution_id.
    """
    if observation.execution_id not in _MOCK_EXECUTION_STORE:
        raise HTTPException(status_code=404, detail="Execution not found. Observations must reference a valid execution.")

    execution = _MOCK_EXECUTION_STORE[observation.execution_id]

    # Hash check: ensuring observation correctly maps to the exact executed plan
    if observation.plan_hash != execution.plan_hash:
        raise HTTPException(
            status_code=400,
            detail="Plan hash mismatch. Observation plan hash does not match the execution plan hash."
        )

    # In a real system, persist to ObservationRecordORM here
    _MOCK_OBSERVATION_STORE.append(observation)

    return observation


@router.post(
    "/intelligence/outcomes/verify/{execution_id}",
    response_model=OutcomeAssessment,
    summary="Deterministically verify the outcome of an execution",
)
async def verify_outcome(
    request: Request,
    execution_id: str,
) -> OutcomeAssessment:
    """
    Calculates the final OutcomeAssessment based on recorded ExecutionResult and Observations.
    """
    if execution_id not in _MOCK_EXECUTION_STORE:
        raise HTTPException(status_code=404, detail="Execution not found.")

    execution = _MOCK_EXECUTION_STORE[execution_id]
    observations = [obs for obs in _MOCK_OBSERVATION_STORE if obs.execution_id == execution_id]

    engine: VerificationEngine = request.app.state.verification_engine

    assessment = engine.verify(execution=execution, observations=observations)

    # In a real system, persist to OutcomeAssessmentORM here
    _MOCK_ASSESSMENT_STORE.append(assessment)

    return assessment
