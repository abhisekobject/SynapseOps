"""
Unit tests — Simulation API Routes.

Tests all simulation REST endpoints using FastAPI TestClient with
mocked FailureController. No real Redis, DB, or network required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.simulation.models import (
    ClearFailuresResponse,
    FailureScenario,
    FailureTarget,
    FailureType,
    InjectFailureResponse,
    SimulationState,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_scenario(
    failure_type: FailureType = FailureType.LATENCY,
    target: FailureTarget = FailureTarget.WORKER,
    severity: float = 0.5,
    active: bool = True,
) -> FailureScenario:
    return FailureScenario(
        name="test_scenario",
        failure_type=failure_type,
        target=target,
        severity=severity,
        active=active,
    )


def _make_inject_response(scenario: FailureScenario | None = None) -> InjectFailureResponse:
    s = scenario or _make_scenario()
    return InjectFailureResponse(
        scenario=s,
        message=f"Failure '{s.name}' injected.",
    )


@pytest.fixture
def mock_controller() -> MagicMock:
    """Mock FailureController with sensible return values."""
    controller = MagicMock()

    # Default: empty state
    controller.get_state = AsyncMock(
        return_value=SimulationState(active_scenarios=[], snapshot_at=datetime.now(UTC))
    )
    controller.inject_failure = AsyncMock(return_value=_make_inject_response())
    controller.clear_failures = AsyncMock(
        return_value=ClearFailuresResponse(cleared_count=0, message="No failures to clear.")
    )

    return controller


@pytest.fixture
def client(mock_controller: MagicMock) -> TestClient:
    """TestClient with a mocked FailureController on app.state."""
    app = create_app()
    app.state.failure_controller = mock_controller
    # Stub out other state the health routes need
    app.state.session_factory = MagicMock()
    app.state.redis_client = AsyncMock()
    app.state.engine = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /api/v1/simulation/state
# ---------------------------------------------------------------------------


class TestGetSimulationState:
    def test_returns_200_with_empty_state(self, client: TestClient, mock_controller: MagicMock):
        response = client.get("/api/v1/simulation/state")
        assert response.status_code == 200

    def test_state_response_has_active_scenarios(self, client: TestClient, mock_controller: MagicMock):
        data = client.get("/api/v1/simulation/state").json()
        assert "active_scenarios" in data
        assert "total_active" in data

    def test_state_with_active_failures(self, client: TestClient, mock_controller: MagicMock):
        scenario = _make_scenario(failure_type=FailureType.CRASH)
        mock_controller.get_state = AsyncMock(
            return_value=SimulationState(
                active_scenarios=[scenario],
                snapshot_at=datetime.now(UTC),
            )
        )
        data = client.get("/api/v1/simulation/state").json()
        assert data["total_active"] == 1
        assert len(data["active_scenarios"]) == 1
        assert data["active_scenarios"][0]["failure_type"] == "crash"


# ---------------------------------------------------------------------------
# POST /api/v1/simulation/failures/inject
# ---------------------------------------------------------------------------


class TestInjectFailure:
    def test_inject_returns_201(self, client: TestClient):
        payload = {
            "failure_type": "latency",
            "target": "worker",
            "severity": 0.6,
        }
        response = client.post("/api/v1/simulation/failures/inject", json=payload)
        assert response.status_code == 201

    def test_inject_with_scenario_name(self, client: TestClient, mock_controller: MagicMock):
        # Configure controller to return a crash scenario
        crash_scenario = _make_scenario(failure_type=FailureType.CRASH, target=FailureTarget.WORKER)
        mock_controller.inject_failure = AsyncMock(
            return_value=_make_inject_response(crash_scenario)
        )
        response = client.post(
            "/api/v1/simulation/failures/inject",
            json={"scenario_name": "WORKER_CRASH"},
        )
        assert response.status_code == 201

    def test_inject_unknown_scenario_name_returns_422(self, client: TestClient):
        response = client.post(
            "/api/v1/simulation/failures/inject",
            json={"scenario_name": "DOES_NOT_EXIST"},
        )
        assert response.status_code == 422

    def test_inject_custom_without_failure_type_returns_422(self, client: TestClient):
        """Custom injection without failure_type should be rejected."""
        response = client.post(
            "/api/v1/simulation/failures/inject",
            json={"target": "worker", "severity": 0.5},
        )
        assert response.status_code == 422

    def test_inject_custom_without_target_returns_422(self, client: TestClient):
        """Custom injection without target should be rejected."""
        response = client.post(
            "/api/v1/simulation/failures/inject",
            json={"failure_type": "crash", "severity": 0.5},
        )
        assert response.status_code == 422

    def test_inject_response_contains_scenario(self, client: TestClient):
        response = client.post(
            "/api/v1/simulation/failures/inject",
            json={"failure_type": "latency", "target": "gateway", "severity": 0.8},
        )
        data = response.json()
        assert "scenario" in data
        assert "message" in data

    def test_inject_invalid_severity_returns_422(self, client: TestClient):
        response = client.post(
            "/api/v1/simulation/failures/inject",
            json={"failure_type": "crash", "target": "worker", "severity": 2.0},
        )
        assert response.status_code == 422

    def test_controller_called_with_request(self, client: TestClient, mock_controller: MagicMock):
        client.post(
            "/api/v1/simulation/failures/inject",
            json={"failure_type": "crash", "target": "worker", "severity": 1.0},
        )
        mock_controller.inject_failure.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /api/v1/simulation/failures
# ---------------------------------------------------------------------------


class TestClearFailures:
    def test_clear_returns_200(self, client: TestClient, mock_controller: MagicMock):
        mock_controller.clear_failures = AsyncMock(
            return_value=ClearFailuresResponse(cleared_count=0, message="Cleared 0 scenarios.")
        )
        response = client.delete("/api/v1/simulation/failures")
        assert response.status_code == 200

    def test_clear_response_has_cleared_count(self, client: TestClient, mock_controller: MagicMock):
        mock_controller.clear_failures = AsyncMock(
            return_value=ClearFailuresResponse(cleared_count=3, message="Cleared 3 scenarios.")
        )
        data = client.delete("/api/v1/simulation/failures").json()
        assert data["cleared_count"] == 3
        assert "message" in data

    def test_clear_with_target_body(self, client: TestClient, mock_controller: MagicMock):
        mock_controller.clear_failures = AsyncMock(
            return_value=ClearFailuresResponse(cleared_count=1, message="Cleared 1 scenario for worker.")
        )
        response = client.request(
            "DELETE",
            "/api/v1/simulation/failures",
            json={"target": "worker"},
        )
        assert response.status_code == 200

    def test_controller_clear_is_called(self, client: TestClient, mock_controller: MagicMock):
        mock_controller.clear_failures = AsyncMock(
            return_value=ClearFailuresResponse(cleared_count=0, message="Cleared 0.")
        )
        client.delete("/api/v1/simulation/failures")
        mock_controller.clear_failures.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/v1/simulation/scenarios
# ---------------------------------------------------------------------------


class TestListScenarios:
    def test_returns_200(self, client: TestClient):
        response = client.get("/api/v1/simulation/scenarios")
        assert response.status_code == 200

    def test_returns_ten_scenarios(self, client: TestClient):
        data = client.get("/api/v1/simulation/scenarios").json()
        assert data["total"] == 10

    def test_scenarios_list_has_required_fields(self, client: TestClient):
        data = client.get("/api/v1/simulation/scenarios").json()
        for scenario in data["scenarios"]:
            assert "name" in scenario
            assert "failure_type" in scenario
            assert "target" in scenario
            assert "severity" in scenario
            assert "description" in scenario

    def test_known_scenario_names_present(self, client: TestClient):
        data = client.get("/api/v1/simulation/scenarios").json()
        names = {s["name"] for s in data["scenarios"]}
        assert "WORKER_CRASH" in names
        assert "CASCADE_FAILURE" in names
        assert "API_ERROR_RATE_SPIKE" in names


# ---------------------------------------------------------------------------
# POST /api/v1/simulation/scenarios/{name}/activate
# ---------------------------------------------------------------------------


class TestActivateScenario:
    def test_activate_known_scenario_returns_201(self, client: TestClient, mock_controller: MagicMock):
        response = client.post("/api/v1/simulation/scenarios/WORKER_CRASH/activate")
        assert response.status_code == 201

    def test_activate_unknown_scenario_returns_404(self, client: TestClient):
        response = client.post("/api/v1/simulation/scenarios/NONEXISTENT/activate")
        assert response.status_code == 404

    def test_activate_calls_controller_inject(self, client: TestClient, mock_controller: MagicMock):
        client.post("/api/v1/simulation/scenarios/WORKER_CRASH/activate")
        mock_controller.inject_failure.assert_called_once()

    def test_activate_all_known_scenarios(self, client: TestClient, mock_controller: MagicMock):
        scenario_names = [
            "WORKER_CRASH", "API_ERROR_RATE_SPIKE", "DB_CONNECTION_EXHAUSTION",
            "CPU_PRESSURE_WORKER", "CASCADE_FAILURE", "GATEWAY_LATENCY",
            "MEMORY_PRESSURE_API", "NETWORK_PARTITION_WORKER", "REDIS_TIMEOUT",
            "DOWNSTREAM_TIMEOUT",
        ]
        for name in scenario_names:
            response = client.post(f"/api/v1/simulation/scenarios/{name}/activate")
            assert response.status_code == 201, f"Failed for scenario: {name}"


# ---------------------------------------------------------------------------
# Missing controller (503 tests)
# ---------------------------------------------------------------------------


class TestMissingController:
    @pytest.fixture
    def client_no_controller(self) -> TestClient:
        """TestClient where failure_controller is NOT set on app.state."""
        app = create_app()
        app.state.session_factory = MagicMock()
        app.state.redis_client = AsyncMock()
        app.state.engine = MagicMock()
        # Deliberately NOT setting app.state.failure_controller
        return TestClient(app, raise_server_exceptions=False)

    def test_inject_without_controller_returns_503(self, client_no_controller: TestClient):
        response = client_no_controller.post(
            "/api/v1/simulation/failures/inject",
            json={"failure_type": "crash", "target": "worker", "severity": 1.0},
        )
        assert response.status_code == 503

    def test_state_without_controller_returns_503(self, client_no_controller: TestClient):
        response = client_no_controller.get("/api/v1/simulation/state")
        assert response.status_code == 503

    def test_clear_without_controller_returns_503(self, client_no_controller: TestClient):
        response = client_no_controller.delete("/api/v1/simulation/failures")
        assert response.status_code == 503
