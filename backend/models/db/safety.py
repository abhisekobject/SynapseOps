import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class PolicyDecisionORM(Base):
    """Persisted record of a deterministic Policy Engine evaluation."""
    __tablename__ = "policy_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String, index=True)
    decision: Mapped[str] = mapped_column(String)  # ALLOW, DENY, REQUIRES_APPROVAL
    policy_version: Mapped[str] = mapped_column(String)
    risk_level: Mapped[str] = mapped_column(String)
    reasons: Mapped[list[str]] = mapped_column(JSON)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ApprovalRequestORM(Base):
    """Persisted record of a human approval state machine."""
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)  # PENDING, APPROVED, REJECTED, EXPIRED
    requested_by: Mapped[str] = mapped_column(String)
    approver: Mapped[str | None] = mapped_column(String, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SafetyAuditEventORM(Base):
    """Append-only audit trail for Phase 9 safety operations."""
    __tablename__ = "safety_audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String, index=True)  # POLICY_EVALUATED, APPROVAL_REQUESTED, APPROVAL_GRANTED, APPROVAL_REJECTED
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String)
    principal: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
