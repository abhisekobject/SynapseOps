import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base


class ExecutionRecordORM(Base):
    """Append-only audit ledger for Phase 10 execution attempts."""
    __tablename__ = "execution_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String, index=True)
    approval_id: Mapped[str] = mapped_column(String, index=True)
    plan_hash: Mapped[str] = mapped_column(String)
    action_type: Mapped[str] = mapped_column(String)
    target_component: Mapped[str] = mapped_column(String)
    executor_type: Mapped[str] = mapped_column(String)
    execution_mode: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)  # SUCCESS, FAILED, TIMEOUT, REJECTED
    error_category: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
