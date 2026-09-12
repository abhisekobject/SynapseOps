"""Add feedback tables for Phase 12

Revision ID: 005
Revises: 004
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("outcome_state", sa.String(), nullable=False),
        sa.Column("feedback_type", sa.String(), nullable=False),
        sa.Column("causal_attribution", sa.String(), nullable=False),
        sa.Column("quality_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_feedback_records_assessment_id", "feedback_records", ["assessment_id"])
    op.create_index("ix_feedback_records_execution_id", "feedback_records", ["execution_id"])
    op.create_index("ix_feedback_records_plan_id", "feedback_records", ["plan_id"])

    op.create_table(
        "learning_signal_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("feedback_id", sa.String(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("expected_result", sa.String(), nullable=False),
        sa.Column("observed_result", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_learning_signal_records_feedback_id", "learning_signal_records", ["feedback_id"])

    op.create_table(
        "learning_decision_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("signal_id", sa.String(), nullable=False),
        sa.Column("decision_state", sa.String(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_learning_decision_records_signal_id", "learning_decision_records", ["signal_id"])


def downgrade() -> None:
    op.drop_table("learning_decision_records")
    op.drop_table("learning_signal_records")
    op.drop_table("feedback_records")
