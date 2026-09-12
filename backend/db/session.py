"""
SynapseOps Database Session Management.

Provides the async session factory and FastAPI dependency for obtaining
a database session per request.
"""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.core.errors import DatabaseError
from backend.core.logging import get_logger

logger = get_logger("db.session")


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create and return the async session factory bound to the given engine.

    Args:
        engine: The async SQLAlchemy engine.

    Returns:
        An async_sessionmaker configured for per-request session lifecycle.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Avoid lazy-load issues after commit
        autoflush=True,
        autocommit=False,
    )



async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session for the request lifecycle.

    Usage in a route:
        from fastapi import Depends
        from backend.db.session import get_db_session

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            ...

    The session is committed on success and rolled back on exception.
    """
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Database session error, rolling back", error=str(exc))
            raise DatabaseError("Database session error") from exc
        finally:
            await session.close()
