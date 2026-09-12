from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database ORM model for persisting operational events (Phase 4)."""

    __tablename__ = "events"

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)

    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<EventORM id={self.id} type={self.event_type} service={self.service_id}>"
