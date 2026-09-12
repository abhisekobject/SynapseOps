import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from backend.intelligence.recovery.models import RecoveryPlan


class PolicyDecisionStatus(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class AuthorizationContext(BaseModel):
    """Represents the principal attempting to perform an action."""
    principal: str = Field(description="The unique identity (e.g., username or system ID) making the request.")
    roles: list[str] = Field(default_factory=list, description="Roles bound to this principal.")
    permissions: list[str] = Field(default_factory=list, description="Explicit permissions.")


class PolicyDecision(BaseModel):
    """The output of the deterministic Policy Engine."""
    decision_id: str
    plan_id: str
    plan_hash: str
    decision: PolicyDecisionStatus
    policy_version: str
    risk_level: str
    reasons: list[str]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRequestResponse(BaseModel):
    """Response model for human approval requests."""
    approval_id: str
    plan_id: str
    plan_hash: str
    status: ApprovalStatus
    requested_by: str
    requested_at: datetime
    expires_at: datetime


class PlanIntegrity:
    """Utility class to compute cryptographic hashes of recovery plans to detect tampering."""
    
    @staticmethod
    def compute_hash(plan: RecoveryPlan) -> str:
        """
        Computes a SHA-256 hash of the canonicalized recovery plan.
        Ignores ephemeral fields like UI timestamps and internal `is_validated` flags.
        """
        # Canonicalization: extract strictly the execution-relevant parts
        canonical_steps = []
        for step in plan.steps:
            canonical_steps.append({
                "action_type": step.action_type.value,
                "target_component": step.target_component,
                "estimated_risk": step.estimated_risk.value,
            })
            
        canonical_plan = {
            "plan_id": plan.plan_id,
            "incident_id": plan.incident_id,
            "steps": canonical_steps,
        }
        
        # Ensure consistent ordering and no spaces for reliable hashing
        serialized = json.dumps(canonical_plan, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
