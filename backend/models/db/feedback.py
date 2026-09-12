import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class FeedbackRecordORM(Base):
    """Append-only audit ledger for Feedback."""
    __tablename__ = "feedback_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(String, index=True)
    execution_id: Mapped[str] = mapped_column(String, index=True)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String)

    outcome_state: Mapped[str] = mapped_column(String)
    feedback_type: Mapped[str] = mapped_column(String)
    causal_attribution: Mapped[str] = mapped_column(String)
    quality_payload: Mapped[dict] = mapped_column(JSON)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    metadata_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class LearningSignalRecordORM(Base):
    """Append-only audit ledger for Learning Signals."""
    __tablename__ = "learning_signal_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    feedback_id: Mapped[str] = mapped_column(String, index=True)
    signal_type: Mapped[str] = mapped_column(String)

    expected_result: Mapped[str] = mapped_column(String)
    observed_result: Mapped[str] = mapped_column(String)

    confidence: Mapped[float] = mapped_column(Float)
    is_simulated: Mapped[bool] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class LearningDecisionRecordORM(Base):
    """Append-only audit ledger for Learning Decisions."""
    __tablename__ = "learning_decision_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(String, index=True)
    decision_state: Mapped[str] = mapped_column(String)
    explanation: Mapped[str] = mapped_column(Text)

    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
