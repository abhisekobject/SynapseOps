"""
Alembic Environment Configuration — SynapseOps.

Configures Alembic to use the application's SQLAlchemy metadata
and settings-based database URL for migrations.

Note: Alembic runs synchronously. We use the synchronous psycopg2 driver URL
(database_url_sync) from Settings, not the async asyncpg URL.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the project root is on the path so 'backend' is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import get_settings
from backend.models.db.action import ActionORM  # noqa: F401
from backend.models.db.anomaly import AnomalyORM  # noqa: F401

# Import ALL ORM models so Alembic can detect them via Base.metadata.
# Every new ORM model added in future phases must be imported here.
from backend.models.db.base import Base
from backend.models.db.event import EventORM  # noqa: F401
from backend.models.db.execution import ExecutionRecordORM  # noqa: F401
from backend.models.db.incident import IncidentORM  # noqa: F401
from backend.models.db.observation import ObservationRecordORM, OutcomeAssessmentORM  # noqa: F401
from backend.models.db.outcome import OutcomeORM  # noqa: F401
from backend.models.db.safety import (  # noqa: F401
    ApprovalRequestORM,
    PolicyDecisionORM,
    SafetyAuditEventORM,
)
from backend.models.db.state import StateTransitionORM  # noqa: F401

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use our ORM metadata for autogenerate support
target_metadata = Base.metadata

# Override the sqlalchemy.url from our application settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL output only, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
