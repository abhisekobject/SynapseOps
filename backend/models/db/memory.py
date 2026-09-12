import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class ExperienceRecordORM(Base):
    """Append-only audit ledger for Episodic Experiences."""
    __tablename__ = "experience_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    incident_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    learning_signal_id: Mapped[str] = mapped_column(String, index=True)
    feedback_id: Mapped[str] = mapped_column(String, index=True)
    assessment_id: Mapped[str] = mapped_column(String, index=True)
    execution_id: Mapped[str] = mapped_column(String, index=True)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String)

    target_component: Mapped[str] = mapped_column(String)
    action_type: Mapped[str] = mapped_column(String)
    expected_outcome: Mapped[str] = mapped_column(String)
    observed_outcome: Mapped[str] = mapped_column(String)
    outcome_state: Mapped[str] = mapped_column(String)
    feedback_type: Mapped[str] = mapped_column(String)
    learning_signal_type: Mapped[str] = mapped_column(String)

    is_simulated: Mapped[bool] = mapped_column(Boolean)
    environment: Mapped[str] = mapped_column(String, index=True, default="UNKNOWN")
    fingerprint: Mapped[str] = mapped_column(String, index=True)

    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    metadata_payload: Mapped[dict] = mapped_column(JSON, default=dict)
