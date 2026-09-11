"""
SynapseOps Database ORM Base.

Defines the declarative base and shared mixins used by all ORM models.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all SynapseOps ORM models."""

    pass


class TimestampMixin:
    """Adds created_at and updated_at columns to any ORM model.

    All SynapseOps tables include these timestamps for audit and debugging.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="UTC timestamp of record creation",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        comment="UTC timestamp of last update",
    )


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column to any ORM model."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique record identifier",
    )
