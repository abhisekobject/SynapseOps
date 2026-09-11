"""
Unit tests — Health API Endpoints.

Tests the /health, /health/live, and /health/ready endpoints.
Uses mocked app state — no real DB or Redis required.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client_with_healthy_deps() -> TestClient:
    """TestClient with DB and Redis mocked as healthy."""
    app = create_app()

    # Mock session that responds to SELECT 1
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_session_ctx)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    app.state.session_factory = mock_session_factory
    app.state.redis_client = mock_redis
    app.state.engine = MagicMock()

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_with_unavailable_deps() -> TestClient:
    """TestClient with DB and Redis mocked as unavailable."""
    app = create_app()

    # Mock session factory that raises on execute
    mock_session_factory = MagicMock(side_effect=Exception("DB unavailable"))

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Redis unavailable"))

    app.state.session_factory = mock_session_factory
    app.state.redis_client = mock_redis
    app.state.engine = MagicMock()

    return TestClient(app, raise_server_exceptions=False)


class TestLivenessEndpoint:
    def test_liveness_returns_200(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/health/live")
        assert response.status_code == 200

    def test_liveness_returns_alive_status(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/health/live")
        assert response.json()["status"] == "alive"

    def test_liveness_does_not_check_db(self, client_with_unavailable_deps):
        """Liveness must not depend on external services."""
        response = client_with_unavailable_deps.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestHealthSummaryEndpoint:
    def test_health_summary_returns_200(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/health")
        assert response.status_code == 200

    def test_health_summary_contains_app_name(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/health")
        data = response.json()
        assert "app" in data
        assert data["status"] == "ok"

    def test_health_summary_contains_phase(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/health")
        assert "Phase 1" in response.json()["phase"]


class TestOpenAPIDocumentation:
    def test_openapi_schema_is_accessible(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/openapi.json")
        assert response.status_code == 200

    def test_docs_endpoint_is_accessible(self, client_with_healthy_deps):
        response = client_with_healthy_deps.get("/docs")
        assert response.status_code == 200
