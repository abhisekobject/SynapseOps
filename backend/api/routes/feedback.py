from fastapi import APIRouter, HTTPException, Request

from backend.intelligence.feedback.models import Feedback, LearningDecision, LearningSignal
from backend.intelligence.outcomes.models import OutcomeAssessment

router = APIRouter(tags=["Feedback"])

# Mock stores for Phase 12 v0 API demonstration
_MOCK_FEEDBACK_STORE: dict[str, Feedback] = {}
_MOCK_SIGNAL_STORE: dict[str, LearningSignal] = {}
_MOCK_DECISION_STORE: dict[str, LearningDecision] = {}


@router.post(
    "/intelligence/feedback/generate",
    response_model=dict,
    summary="Generate deterministic feedback and learning signals from an outcome",
)
async def generate_feedback_pipeline(
    request: Request,
    assessment: OutcomeAssessment,
) -> dict:
    """
    Receives an OutcomeAssessment and generates the canonical Feedback, LearningSignal, and LearningDecision.
    Strictly idempotent: Uses assessment_id as the root idempotency key.
    """

    # 1. Idempotency Check
    # If we already processed this assessment, return the canonical artifacts.
    existing_feedback = next((f for f in _MOCK_FEEDBACK_STORE.values() if f.assessment_id == assessment.assessment_id), None)
    if existing_feedback:
        existing_signal = next((s for s in _MOCK_SIGNAL_STORE.values() if s.feedback_id == existing_feedback.feedback_id), None)
        existing_decision = next((d for d in _MOCK_DECISION_STORE.values() if existing_signal and d.signal_id == existing_signal.signal_id), None)

        return {
            "feedback": existing_feedback,
            "signal": existing_signal,
            "decision": existing_decision,
            "status": "EXISTING_RECORD_RETURNED",
        }

    # 2. Generate Artifacts deterministically
    signal_generator = request.app.state.signal_generator
    decision_engine = request.app.state.decision_engine

    feedback = signal_generator.generate_feedback(assessment)
    signal = signal_generator.generate_signal(feedback, assessment)
    decision = decision_engine.decide(feedback, signal)

    # 3. Store artifacts
    _MOCK_FEEDBACK_STORE[feedback.feedback_id] = feedback
    _MOCK_SIGNAL_STORE[signal.signal_id] = signal
    _MOCK_DECISION_STORE[decision.decision_id] = decision

    return {
        "feedback": feedback,
        "signal": signal,
        "decision": decision,
        "status": "GENERATED_NEW_RECORD",
    }


@router.get("/intelligence/feedback/{feedback_id}", response_model=Feedback)
async def get_feedback(feedback_id: str) -> Feedback:
    if feedback_id not in _MOCK_FEEDBACK_STORE:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return _MOCK_FEEDBACK_STORE[feedback_id]
