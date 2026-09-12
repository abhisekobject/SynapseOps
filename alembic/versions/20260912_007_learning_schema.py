"""Add learning tables for Phase 14

Revision ID: 007
Revises: 006
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experience_learning_signals",
        sa.Column("id", sa.String(), primary_key=True),
        # Unique per experience: DB-level idempotency enforcement
        sa.Column("experience_id", sa.String(), nullable=False, unique=True),
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("target_component", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("environment", sa.String(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("derivation_basis", sa.String(), nullable=False),
        sa.Column("observed_outcome", sa.String(), nullable=False),
        sa.Column("expected_outcome", sa.String(), nullable=False),
        sa.Column("verification_status", sa.String(), nullable=False),
        sa.Column("source_fingerprint", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_els_experience_id", "experience_learning_signals", ["experience_id"])
    op.create_index("ix_els_incident_id", "experience_learning_signals", ["incident_id"])
    op.create_index("ix_els_target_component", "experience_learning_signals", ["target_component"])
    op.create_index("ix_els_action_type", "experience_learning_signals", ["action_type"])
    op.create_index("ix_els_environment", "experience_learning_signals", ["environment"])
    op.create_index("ix_els_is_simulated", "experience_learning_signals", ["is_simulated"])
    op.create_index("ix_els_signal_type", "experience_learning_signals", ["signal_type"])
    op.create_index("ix_els_source_fingerprint", "experience_learning_signals", ["source_fingerprint"])

    op.create_table(
        "operational_knowledge",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("knowledge_id", sa.String(), nullable=False, unique=True),
        sa.Column("target_component", sa.String(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=True),
        sa.Column("environment", sa.String(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=True),
        sa.Column("supporting_experience_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verification_success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verification_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outcome_match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outcome_mismatch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observed_effectiveness", sa.Float(), nullable=True),
        sa.Column("source_fingerprints", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("contributing_signal_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("contributing_experience_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="1.0"),
    )
    op.create_index("ix_ok_knowledge_id", "operational_knowledge", ["knowledge_id"])
    op.create_index("ix_ok_target_component", "operational_knowledge", ["target_component"])
    op.create_index("ix_ok_action_type", "operational_knowledge", ["action_type"])
    op.create_index("ix_ok_environment", "operational_knowledge", ["environment"])
    op.create_index("ix_ok_is_simulated", "operational_knowledge", ["is_simulated"])


def downgrade() -> None:
    op.drop_table("operational_knowledge")
    op.drop_table("experience_learning_signals")
