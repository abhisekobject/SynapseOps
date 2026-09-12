"""Add observation tables for Phase 11

Revision ID: 004
Revises: 003
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("observation_source", sa.String(), nullable=False),
        sa.Column("observed_state", sa.String(), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_observations_execution_id", "observations", ["execution_id"])
    op.create_index("ix_observations_plan_id", "observations", ["plan_id"])

    op.create_table(
        "outcome_assessments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("plan_hash", sa.String(), nullable=False),
        sa.Column("execution_status", sa.String(), nullable=False),
        sa.Column("outcome_status", sa.String(), nullable=False),
        sa.Column("expected_outcome", sa.String(), nullable=False),
        sa.Column("observed_outcome", sa.String(), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "assessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_outcome_assessments_execution_id", "outcome_assessments", ["execution_id"])
    op.create_index("ix_outcome_assessments_plan_id", "outcome_assessments", ["plan_id"])
    op.create_index("ix_outcome_assessments_outcome_status", "outcome_assessments", ["outcome_status"])


def downgrade() -> None:
    op.drop_table("outcome_assessments")
    op.drop_table("observations")
