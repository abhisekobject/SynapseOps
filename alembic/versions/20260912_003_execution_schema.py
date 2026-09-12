"""Add execution tables for Phase 10

Revision ID: 003
Revises: 002
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("approval_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("target_component", sa.String(), nullable=False),
        sa.Column("executor_type", sa.String(), nullable=False),
        sa.Column("execution_mode", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_category", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
    )
    op.create_index("ix_execution_records_plan_id", "execution_records", ["plan_id"])
    op.create_index("ix_execution_records_approval_id", "execution_records", ["approval_id"])
    op.create_index("ix_execution_records_status", "execution_records", ["status"])


def downgrade() -> None:
    op.drop_table("execution_records")
