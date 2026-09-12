import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class ObservationRecordORM(Base):
    """Append-only audit ledger for Phase 11 observations."""
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String, index=True)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    observation_source: Mapped[str] = mapped_column(String)
    observed_state: Mapped[str] = mapped_column(String)
    evidence_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class OutcomeAssessmentORM(Base):
    """Append-only audit ledger for final Phase 11 Outcome Assessments."""
    __tablename__ = "outcome_assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String, index=True)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String)

    execution_status: Mapped[str] = mapped_column(String)
    outcome_status: Mapped[str] = mapped_column(String, index=True)

    expected_outcome: Mapped[str] = mapped_column(String)
    observed_outcome: Mapped[str] = mapped_column(String)

    evidence_payload: Mapped[list] = mapped_column(JSON, default=list)

    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
