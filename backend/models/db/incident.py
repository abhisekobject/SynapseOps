"""SynapseOps ORM model — Incident."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IncidentORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy ORM model for the incidents table.

    Stores incident records persisted throughout the operational loop.
    Maps to the Incident Pydantic domain model.
    """

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="detected")
    affected_services: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list
    )
    probable_root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<IncidentORM id={self.id} title={self.title!r} status={self.status}>"
