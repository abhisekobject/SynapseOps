"""
SynapseOps Test Configuration — conftest.py.

Shared fixtures for the entire test suite.

Test strategy:
  unit/       — No external dependencies. Fast. Use mocks for DB/Redis.
  integration/ — Require running PostgreSQL and Redis. Marked with @pytest.mark.integration.

Running only unit tests (no DB/Redis required):
    pytest tests/unit/ -v

Running all tests (requires running DB + Redis):
    pytest -v

Running with coverage:
    pytest --cov=backend --cov-report=term-missing
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.core.config import Settings
from backend.main import create_app

# =============================================================================
# Settings Fixtures
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Return a Settings instance with test-safe defaults.

    Does not read from .env — uses explicit test values.
    Override individual fields in tests as needed.
    """
    return Settings(
        app_name="SynapseOps-Test",
        environment="test",
        debug=True,
        log_level="WARNING",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="synapseops_test",
        postgres_user="synapseops",
        postgres_password="test_password",
        redis_host="localhost",
        redis_port=6379,
        redis_db=1,  # Use DB 1 to avoid colliding with development DB 0
    )


# =============================================================================
# Application Fixtures
# =============================================================================


@pytest.fixture
def app_with_mocked_state(test_settings: Settings):
    """Return a FastAPI app instance with mocked DB and Redis state.

    Suitable for unit tests of API routes that don't need real DB/Redis.
    The app.state is populated with AsyncMock objects.
    """
    app = create_app()

    # Mock session factory — returns a context manager that yields an async session
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    app.state.session_factory = mock_session_factory
    app.state.redis_client = mock_redis
    app.state.engine = MagicMock()

    return app


@pytest.fixture
def client(app_with_mocked_state) -> TestClient:
    """Return a synchronous TestClient wrapping the mocked app.

    Uses TestClient (not AsyncClient) for simplicity in unit tests.
    Integration tests use httpx.AsyncClient.
    """
    return TestClient(app_with_mocked_state, raise_server_exceptions=True)
