"""SynapseOps ORM model — Anomaly."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnomalyORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy ORM model for the anomalies table."""

    __tablename__ = "anomalies"

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated incident (set when correlated)",
    )
    anomaly_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AnomalyORM id={self.id} service={self.service_name!r} "
            f"type={self.anomaly_type} status={self.status}>"
        )
