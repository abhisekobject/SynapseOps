from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StateTransitionORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database ORM model for tracking service state transitions (Phase 4)."""

    __tablename__ = "state_transitions"

    service_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<StateTransitionORM service={self.service_id} {self.previous_status}->{self.new_status}>"
