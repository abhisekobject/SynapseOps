"""Add safety tables for Phase 9

Revision ID: 002
Revises: 001
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_decisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_policy_decisions_plan_id", "policy_decisions", ["plan_id"])
    op.create_index("ix_policy_decisions_plan_hash", "policy_decisions", ["plan_hash"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("requested_by", sa.String(), nullable=False),
        sa.Column("approver", sa.String(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approval_requests_plan_id", "approval_requests", ["plan_id"])
    op.create_index("ix_approval_requests_plan_hash", "approval_requests", ["plan_hash"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    op.create_table(
        "safety_audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("principal", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_safety_audit_events_event_type", "safety_audit_events", ["event_type"])
    op.create_index("ix_safety_audit_events_plan_id", "safety_audit_events", ["plan_id"])
    op.create_index("ix_safety_audit_events_timestamp", "safety_audit_events", ["timestamp"])


def downgrade() -> None:
    op.drop_table("safety_audit_events")
    op.drop_table("approval_requests")
    op.drop_table("policy_decisions")
