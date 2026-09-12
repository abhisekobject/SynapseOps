"""
Unit tests — FailureController.

Tests the simulation failure controller in isolation using a mock Redis client.
No real Redis, no network, no filesystem required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from backend.simulation.controller import FailureController
from backend.simulation.models import (
    ClearFailuresRequest,
    FailureScenario,
    FailureTarget,
    FailureType,
    InjectFailureRequest,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client — set/get return None by default."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    return redis


@pytest.fixture
def controller(mock_redis: AsyncMock) -> FailureController:
    """FailureController backed by a mock Redis client."""
    return FailureController(redis_client=mock_redis, redis_failure_key="test:failures")


def _make_inject_request(
    failure_type: FailureType = FailureType.LATENCY,
    target: FailureTarget = FailureTarget.WORKER,
    severity: float = 0.5,
    duration_seconds: float | None = 300.0,
    name: str = "test_failure",
) -> InjectFailureRequest:
    return InjectFailureRequest(
        name=name,
        failure_type=failure_type,
        target=target,
        severity=severity,
        duration_seconds=duration_seconds,
    )


# ---------------------------------------------------------------------------
# Injection tests
# ---------------------------------------------------------------------------


class TestFailureControllerInject:
    async def test_inject_creates_scenario(self, controller: FailureController):
        req = _make_inject_request()
        resp = await controller.inject_failure(req)
        assert resp.scenario.failure_type == FailureType.LATENCY
        assert resp.scenario.target == FailureTarget.WORKER
        assert resp.scenario.active is True

    async def test_inject_stores_scenario_in_memory(self, controller: FailureController):
        req = _make_inject_request()
        await controller.inject_failure(req)
        state = await controller.get_state()
        assert state.total_active == 1

    async def test_inject_multiple_scenarios(self, controller: FailureController):
        await controller.inject_failure(_make_inject_request(name="f1"))
        await controller.inject_failure(
            _make_inject_request(name="f2", failure_type=FailureType.CRASH)
        )
        state = await controller.get_state()
        assert state.total_active == 2

    async def test_inject_publishes_to_redis(
        self, controller: FailureController, mock_redis: AsyncMock
    ):
        req = _make_inject_request()
        await controller.inject_failure(req)
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        # First positional arg should be the Redis key
        assert "test:failures" in str(call_args)

    async def test_inject_response_has_message(self, controller: FailureController):
        req = _make_inject_request()
        resp = await controller.inject_failure(req)
        assert len(resp.message) > 0
        assert resp.scenario.name in resp.message or resp.scenario.failure_type in resp.message

    async def test_injected_scenario_has_unique_id(self, controller: FailureController):
        resp1 = await controller.inject_failure(_make_inject_request(name="a"))
        resp2 = await controller.inject_failure(_make_inject_request(name="b"))
        assert resp1.scenario.id != resp2.scenario.id


# ---------------------------------------------------------------------------
# Clear tests
# ---------------------------------------------------------------------------


class TestFailureControllerClear:
    async def test_clear_all_removes_all_scenarios(self, controller: FailureController):
        await controller.inject_failure(_make_inject_request(name="f1"))
        await controller.inject_failure(_make_inject_request(name="f2"))
        resp = await controller.clear_failures(ClearFailuresRequest(target=None))
        assert resp.cleared_count == 2
        state = await controller.get_state()
        assert state.total_active == 0

    async def test_clear_by_target_only_removes_matching(self, controller: FailureController):
        await controller.inject_failure(_make_inject_request(target=FailureTarget.WORKER))
        await controller.inject_failure(_make_inject_request(target=FailureTarget.GATEWAY))
        resp = await controller.clear_failures(ClearFailuresRequest(target=FailureTarget.WORKER))
        assert resp.cleared_count == 1
        state = await controller.get_state()
        assert state.total_active == 1
        remaining = state.active_scenarios[0]
        assert remaining.target == FailureTarget.GATEWAY

    async def test_clear_empty_state_returns_zero(self, controller: FailureController):
        resp = await controller.clear_failures(ClearFailuresRequest())
        assert resp.cleared_count == 0

    async def test_clear_publishes_empty_state_to_redis(
        self, controller: FailureController, mock_redis: AsyncMock
    ):
        await controller.inject_failure(_make_inject_request())
        mock_redis.set.reset_mock()
        await controller.clear_failures(ClearFailuresRequest())
        mock_redis.set.assert_called_once()

    async def test_clear_by_all_target_removes_everything(self, controller: FailureController):
        await controller.inject_failure(_make_inject_request(target=FailureTarget.ALL))
        await controller.inject_failure(_make_inject_request(target=FailureTarget.WORKER))
        resp = await controller.clear_failures(ClearFailuresRequest(target=FailureTarget.ALL))
        assert resp.cleared_count == 2


# ---------------------------------------------------------------------------
# State query tests
# ---------------------------------------------------------------------------


class TestFailureControllerGetState:
    async def test_initial_state_is_healthy(self, controller: FailureController):
        state = await controller.get_state()
        assert state.is_healthy() is True
        assert state.total_active == 0

    async def test_state_reflects_active_scenarios(self, controller: FailureController):
        await controller.inject_failure(_make_inject_request())
        state = await controller.get_state()
        assert len(state.active_scenarios) == 1

    async def test_state_snapshot_at_is_recent(self, controller: FailureController):
        state = await controller.get_state()
        now = datetime.now(UTC)
        diff = abs((now - state.snapshot_at).total_seconds())
        assert diff < 2.0  # Should be within 2 seconds


# ---------------------------------------------------------------------------
# Active failures for target
# ---------------------------------------------------------------------------


class TestGetActiveFailuresForTarget:
    async def test_returns_scenarios_for_matching_target(self, controller: FailureController):
        await controller.inject_failure(_make_inject_request(target=FailureTarget.WORKER))
        await controller.inject_failure(_make_inject_request(target=FailureTarget.GATEWAY))
        failures = await controller.get_active_failures_for(FailureTarget.WORKER)
        assert len(failures) == 1
        assert failures[0].target == FailureTarget.WORKER

    async def test_all_target_appears_in_every_query(self, controller: FailureController):
        """A scenario targeting ALL should be returned for any target query."""
        await controller.inject_failure(_make_inject_request(target=FailureTarget.ALL))
        for tgt in [FailureTarget.WORKER, FailureTarget.GATEWAY, FailureTarget.API_SERVICE]:
            failures = await controller.get_active_failures_for(tgt)
            assert len(failures) == 1

    async def test_empty_when_no_failures(self, controller: FailureController):
        failures = await controller.get_active_failures_for(FailureTarget.WORKER)
        assert failures == []


# ---------------------------------------------------------------------------
# Expiry logic
# ---------------------------------------------------------------------------


class TestFailureExpiry:
    async def test_expire_scenarios_removes_expired(self, controller: FailureController):
        """Inject a scenario with a past start time so it's already expired."""
        past = datetime.now(UTC) - timedelta(seconds=500)
        scenario = FailureScenario(
            name="expired",
            failure_type=FailureType.CRASH,
            target=FailureTarget.WORKER,
            severity=1.0,
            duration_seconds=100.0,
            started_at=past,
        )
        # Directly insert into internal store to test expiry
        controller._scenarios[scenario.id] = scenario

        expired_count = await controller._expire_scenarios()
        assert expired_count == 1
        state = await controller.get_state()
        assert state.total_active == 0

    async def test_expire_scenarios_leaves_non_expired(self, controller: FailureController):
        """Inject a scenario that has NOT yet expired — should remain active."""
        req = _make_inject_request(duration_seconds=600.0)
        await controller.inject_failure(req)
        expired_count = await controller._expire_scenarios()
        assert expired_count == 0
        state = await controller.get_state()
        assert state.total_active == 1

    async def test_expire_permanent_scenarios_never_expires(self, controller: FailureController):
        """Scenarios with no duration_seconds should never expire."""
        req = _make_inject_request(duration_seconds=None)
        await controller.inject_failure(req)
        expired_count = await controller._expire_scenarios()
        assert expired_count == 0


# ---------------------------------------------------------------------------
# Redis failure resilience
# ---------------------------------------------------------------------------


class TestRedisFailureResilience:
    async def test_redis_failure_does_not_crash_inject(self, controller: FailureController):
        """If Redis is unavailable, inject_failure should still succeed (in-memory)."""
        controller._redis.set = AsyncMock(side_effect=Exception("Redis down"))
        req = _make_inject_request()
        # Should not raise
        resp = await controller.inject_failure(req)
        assert resp.scenario.active is True
        # State should still reflect the injection
        state = await controller.get_state()
        assert state.total_active == 1
