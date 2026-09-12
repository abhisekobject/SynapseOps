import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from backend.intelligence.recovery.actions import RecoveryActionType
from backend.intelligence.recovery.models import RecoveryPlan
from backend.intelligence.safety.models import ApprovalRequestResponse, AuthorizationContext


class ExecutionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ExecutionAuthorization(BaseModel):
    """The explicit authorization boundary that ExecutionGate enforces."""
    plan: RecoveryPlan
    approval: ApprovalRequestResponse
    auth_context: AuthorizationContext


class ExecutionResult(BaseModel):
    """The structured result of an execution attempt."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    approval_id: str
    plan_hash: str
    action_type: RecoveryActionType
    target: str
    executor_type: str
    execution_mode: str = Field(default="SIMULATED", description="Whether this is real or simulated execution.")
    status: ExecutionStatus
    error_category: str | None = None
    error_message: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_seconds: float | None = None
