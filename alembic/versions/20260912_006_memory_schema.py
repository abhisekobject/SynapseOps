"""Add memory tables for Phase 13

Revision ID: 006
Revises: 005
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experience_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("learning_signal_id", sa.String(), nullable=False),
        sa.Column("feedback_id", sa.String(), nullable=False),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("target_component", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("expected_outcome", sa.String(), nullable=False),
        sa.Column("observed_outcome", sa.String(), nullable=False),
        sa.Column("outcome_state", sa.String(), nullable=False),
        sa.Column("feedback_type", sa.String(), nullable=False),
        sa.Column("learning_signal_type", sa.String(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("environment", sa.String(), nullable=False, server_default="UNKNOWN"),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_experience_records_incident_id", "experience_records", ["incident_id"])
    op.create_index("ix_experience_records_learning_signal_id", "experience_records", ["learning_signal_id"])
    op.create_index("ix_experience_records_feedback_id", "experience_records", ["feedback_id"])
    op.create_index("ix_experience_records_assessment_id", "experience_records", ["assessment_id"])
    op.create_index("ix_experience_records_execution_id", "experience_records", ["execution_id"])
    op.create_index("ix_experience_records_plan_id", "experience_records", ["plan_id"])
    op.create_index("ix_experience_records_environment", "experience_records", ["environment"])
    op.create_index("ix_experience_records_fingerprint", "experience_records", ["fingerprint"])


def downgrade() -> None:
    op.drop_table("experience_records")
