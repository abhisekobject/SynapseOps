"""Initial schema — Phase 1 foundation tables.

Creates the four core SynapseOps tables:
  - incidents
  - anomalies
  - actions
  - outcomes

Revision ID: 001
Revises: (none)
Create Date: 2026-09-11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- incidents ---
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="detected"),
        sa.Column(
            "affected_services",
            postgresql.ARRAY(sa.String(100)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("probable_root_cause", sa.Text, nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # --- anomalies ---
    op.create_table(
        "anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("anomaly_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=True),
        sa.Column("observed_value", sa.Float, nullable=True),
        sa.Column("baseline_value", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_anomalies_incident_id", "anomalies", ["incident_id"])
    op.create_index("ix_anomalies_service_name", "anomalies", ["service_name"])
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])

    # --- actions ---
    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="proposed"),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("target_service", sa.String(100), nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("rollback_description", sa.Text, nullable=True),
        sa.Column(
            "proposed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_actions_incident_id", "actions", ["incident_id"])

    # --- outcomes ---
    op.create_table(
        "outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "action_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_result", sa.String(20), nullable=False),
        sa.Column(
            "recovery_status",
            sa.String(30),
            nullable=False,
            server_default="verification_pending",
        ),
        sa.Column("execution_duration_seconds", sa.Float, nullable=True),
        sa.Column("verification_notes", sa.Text, nullable=True),
        sa.Column("operator_feedback", sa.Text, nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_outcomes_action_id", "outcomes", ["action_id"])
    op.create_index("ix_outcomes_incident_id", "outcomes", ["incident_id"])


def downgrade() -> None:
    op.drop_table("outcomes")
    op.drop_table("actions")
    op.drop_table("anomalies")
    op.drop_table("incidents")
