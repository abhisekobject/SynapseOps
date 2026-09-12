import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class ExperienceLearningSignalORM(Base):
    """Append-only ledger for Phase 14 ExperienceLearningSignals."""
    __tablename__ = "experience_learning_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Idempotency key: one signal per experience
    experience_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    incident_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)

    # Dimensions
    target_component: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String, index=True)
    environment: Mapped[str] = mapped_column(String, index=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, index=True)

    # Classification
    signal_type: Mapped[str] = mapped_column(String, index=True)
    derivation_basis: Mapped[str] = mapped_column(String)

    # Observations
    observed_outcome: Mapped[str] = mapped_column(String)
    expected_outcome: Mapped[str] = mapped_column(String)
    verification_status: Mapped[str] = mapped_column(String)

    # Traceability
    source_fingerprint: Mapped[str] = mapped_column(String, index=True)
    schema_version: Mapped[str] = mapped_column(String, default="1.0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class OperationalKnowledgeORM(Base):
    """Append-only ledger for Phase 14 OperationalKnowledge aggregates."""
    __tablename__ = "operational_knowledge"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Aggregation dimensions (knowledge_id is deterministic from these)
    knowledge_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    target_component: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    action_type: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    environment: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    is_simulated: Mapped[bool | None] = mapped_column(Boolean, index=True, nullable=True)

    # Evidence counts
    supporting_experience_count: Mapped[int] = mapped_column(Integer, default=0)
    successful_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    partial_count: Mapped[int] = mapped_column(Integer, default=0)
    verification_success_count: Mapped[int] = mapped_column(Integer, default=0)
    verification_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    outcome_match_count: Mapped[int] = mapped_column(Integer, default=0)
    outcome_mismatch_count: Mapped[int] = mapped_column(Integer, default=0)

    # Derived statistic (OBSERVATION ONLY — not a prediction)
    observed_effectiveness: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Evidence lists stored as JSON
    source_fingerprints: Mapped[list] = mapped_column(JSON, default=list)
    contributing_signal_ids: Mapped[list] = mapped_column(JSON, default=list)
    contributing_experience_ids: Mapped[list] = mapped_column(JSON, default=list)

    # Temporal
    first_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    schema_version: Mapped[str] = mapped_column(String, default="1.0")
