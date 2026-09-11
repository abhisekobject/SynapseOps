"""
Integration tests — Database connectivity and session management.

These tests require a running PostgreSQL instance.
Run with: pytest tests/integration/ -v -m integration

Skip in CI/unit-only runs: pytest tests/unit/ -v
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires running PostgreSQL — run manually with docker-compose up")
class TestDatabaseConnectivity:
    """Integration tests for database connectivity.

    Prerequisites:
        docker-compose up -d postgres
        # or a running PostgreSQL instance matching .env settings
    """

    async def test_database_engine_connects(self, test_settings):
        """Verify the async engine can establish a connection."""
        from sqlalchemy import text

        from backend.db.engine import create_engine

        engine = create_engine(test_settings)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            await engine.dispose()

    async def test_session_factory_yields_session(self, test_settings):
        """Verify the session factory yields a working AsyncSession."""
        from sqlalchemy import text

        from backend.db.engine import create_engine
        from backend.db.session import create_session_factory

        engine = create_engine(test_settings)
        session_factory = create_session_factory(engine)
        try:
            async with session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            await engine.dispose()
