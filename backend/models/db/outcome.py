"""SynapseOps ORM model — Outcome."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutcomeORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy ORM model for the outcomes table.

    Records the results of recovery actions, including both action-level
    execution results and system-level recovery verification results.

    The separation of action_result and recovery_status is intentional.
    See backend/models/domain/outcome.py for the architectural rationale.
    """

    __tablename__ = "outcomes"

    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_result: Mapped[str] = mapped_column(String(20), nullable=False)
    recovery_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="verification_pending"
    )
    execution_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        return (
            f"<OutcomeORM id={self.id} action_result={self.action_result} "
            f"recovery_status={self.recovery_status}>"
        )
