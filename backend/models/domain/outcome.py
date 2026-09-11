"""
SynapseOps Domain Models — Outcome.

An Outcome records the result of a recovery action and — critically — whether
the system actually recovered after the action was executed.

This model enforces the fundamental verification principle established in Phase 0:

    "Action executed successfully" ≠ "System recovered."

An action may complete without execution error but fail to restore the system to
a healthy state. The Outcome model captures both dimensions separately.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ActionResult(StrEnum):
    """The result of the action execution itself (not the system recovery).

    This is distinct from RecoveryStatus, which measures whether the system
    returned to a healthy state after the action.
    """

    SUCCESS = "success"  # Action executed without error
    FAILURE = "failure"  # Action failed during execution
    TIMEOUT = "timeout"  # Action exceeded its time limit
    ROLLED_BACK = "rolled_back"  # Action was reversed after a failed verification


class RecoveryStatus(StrEnum):
    """Whether the system returned to a healthy baseline after the action.

    This is determined by the Verification Engine (Phase 11) through
    re-observation of relevant telemetry signals.
    """

    RECOVERED = "recovered"  # System returned to healthy baseline
    NOT_RECOVERED = "not_recovered"  # System remains degraded after action
    PARTIALLY_RECOVERED = "partially_recovered"  # Some metrics recovered; others did not
    VERIFICATION_PENDING = "verification_pending"  # Waiting for observation window
    VERIFICATION_FAILED = "verification_failed"  # Verification process itself failed


class Outcome(BaseModel):
    """Pydantic domain model representing the outcome of a recovery action.

    Outcomes are the primary input to the Feedback/Learning layer (Phase 11).
    They are also the ground truth against which recovery effectiveness metrics
    are computed in the evaluation framework (EVALUATION.md).

    The separation of action_result and recovery_status is intentional and
    architecturally important. Future phases will use both fields to:
      - Improve action ranking in the Recovery Planner
      - Update confidence weights in the Policy Engine
      - Inform hypothesis generation in the Diagnosis layer
    """

    id: UUID = Field(default_factory=uuid4, description="Unique outcome identifier")
    action_id: UUID = Field(..., description="The action this outcome records")
    incident_id: UUID = Field(..., description="The incident this outcome is associated with")
    action_result: ActionResult = Field(
        ...,
        description="Whether the action execution itself succeeded or failed",
    )
    recovery_status: RecoveryStatus = Field(
        default=RecoveryStatus.VERIFICATION_PENDING,
        description="Whether the system returned to healthy state after the action",
    )
    execution_duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="How long the action execution took in seconds",
    )
    verification_notes: str | None = Field(
        default=None,
        description="Human-readable notes from the verification process",
    )
    operator_feedback: str | None = Field(
        default=None,
        description="Optional feedback from the human operator on this outcome",
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when this outcome was recorded",
    )

    model_config = {"from_attributes": True}
