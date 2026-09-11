"""
SynapseOps Database Engine.

Creates and configures the async SQLAlchemy engine.
The engine is created once per application lifecycle.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from backend.core.config import Settings
from backend.core.logging import get_logger

logger = get_logger("db.engine")


def create_engine(settings: Settings) -> AsyncEngine:
    """Create and return the async SQLAlchemy engine.

    Args:
        settings: Application settings containing the database URL.

    Returns:
        A configured AsyncEngine instance.

    The engine uses a connection pool suitable for development.
    Pool settings may be tuned in later phases based on load characteristics.
    """
    logger.info(
        "Creating database engine",
        host=settings.postgres_host,
        port=settings.postgres_port,
        db=settings.postgres_db,
    )

    return create_async_engine(
        settings.database_url,
        echo=settings.debug,  # Log SQL statements in debug mode
        pool_pre_ping=True,  # Verify connections before use
        pool_size=5,  # Conservative pool size for Phase 1
        max_overflow=10,
    )
