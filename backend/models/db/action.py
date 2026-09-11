"""SynapseOps ORM model — Action."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActionORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy ORM model for the actions table.

    Records proposed and executed recovery actions.
    The parameters column uses PostgreSQL JSONB for flexibility
    as different action types have different parameter sets.
    """

    __tablename__ = "actions"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="proposed")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    target_service: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ActionORM id={self.id} type={self.action_type} "
            f"target={self.target_service!r} status={self.status}>"
        )
