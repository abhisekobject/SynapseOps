"""
Unit tests — Simulation Domain Models.

Tests Pydantic model creation, validation, and behaviour for all
simulation models. No external dependencies required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.simulation.models import (
    ClearFailuresRequest,
    ClearFailuresResponse,
    FailureScenario,
    FailureTarget,
    FailureType,
    InjectFailureRequest,
    ServiceHealthSnapshot,
    SimulationState,
)

# ---------------------------------------------------------------------------
# FailureType enum
# ---------------------------------------------------------------------------


class TestFailureType:
    def test_all_ten_failure_types_defined(self):
        expected = {
            "crash",
            "latency",
            "cpu_pressure",
            "memory_pressure",
            "db_connection_exhaustion",
            "error_rate_spike",
            "network_partition",
            "disk_io_pressure",
            "downstream_timeout",
            "cascade_slow",
        }
        actual = {t.value for t in FailureType}
        assert actual == expected

    def test_failure_type_is_string_comparable(self):
        assert FailureType.CRASH == "crash"
        assert FailureType.LATENCY == "latency"

    def test_failure_type_from_string(self):
        ft = FailureType("error_rate_spike")
        assert ft == FailureType.ERROR_RATE_SPIKE


# ---------------------------------------------------------------------------
# FailureTarget enum
# ---------------------------------------------------------------------------


class TestFailureTarget:
    def test_all_six_targets_defined(self):
        expected = {"gateway", "api_service", "worker", "database", "redis", "all"}
        actual = {t.value for t in FailureTarget}
        assert actual == expected

    def test_all_target_from_string(self):
        assert FailureTarget("all") == FailureTarget.ALL


# ---------------------------------------------------------------------------
# FailureScenario model
# ---------------------------------------------------------------------------


class TestFailureScenario:
    def _make_scenario(self, **overrides) -> FailureScenario:
        defaults = {
            "name": "test_scenario",
            "failure_type": FailureType.LATENCY,
            "target": FailureTarget.WORKER,
            "severity": 0.5,
        }
        defaults.update(overrides)
        return FailureScenario(**defaults)

    def test_scenario_created_with_defaults(self):
        s = self._make_scenario()
        assert s.name == "test_scenario"
        assert s.failure_type == FailureType.LATENCY
        assert s.target == FailureTarget.WORKER
        assert s.severity == 0.5
        assert s.active is True
        assert s.duration_seconds is None
        assert isinstance(s.id, uuid.UUID)

    def test_scenario_auto_generates_id(self):
        s1 = self._make_scenario()
        s2 = self._make_scenario()
        assert s1.id != s2.id

    def test_severity_lower_bound(self):
        s = self._make_scenario(severity=0.0)
        assert s.severity == 0.0

    def test_severity_upper_bound(self):
        s = self._make_scenario(severity=1.0)
        assert s.severity == 1.0

    def test_severity_below_zero_fails(self):
        with pytest.raises(ValidationError):
            self._make_scenario(severity=-0.1)

    def test_severity_above_one_fails(self):
        with pytest.raises(ValidationError):
            self._make_scenario(severity=1.1)

    def test_duration_seconds_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._make_scenario(duration_seconds=0.0)

    def test_duration_seconds_negative_fails(self):
        with pytest.raises(ValidationError):
            self._make_scenario(duration_seconds=-10.0)

    def test_duration_seconds_none_is_valid(self):
        s = self._make_scenario(duration_seconds=None)
        assert s.duration_seconds is None

    def test_started_at_is_utc(self):
        s = self._make_scenario()
        assert s.started_at.tzinfo is not None

    # ----- is_expired -----

    def test_not_expired_when_duration_none(self):
        s = self._make_scenario(duration_seconds=None)
        assert s.is_expired() is False

    def test_not_expired_when_inactive(self):
        # Inactive scenario is "expired" — returns True
        s = self._make_scenario(active=False)
        assert s.is_expired() is True

    def test_expired_when_past_duration(self):
        started = datetime.now(UTC) - timedelta(seconds=200)
        s = FailureScenario(
            name="x",
            failure_type=FailureType.CRASH,
            target=FailureTarget.GATEWAY,
            severity=1.0,
            duration_seconds=100.0,
            started_at=started,
        )
        assert s.is_expired() is True

    def test_not_expired_within_duration(self):
        started = datetime.now(UTC) - timedelta(seconds=10)
        s = FailureScenario(
            name="x",
            failure_type=FailureType.CRASH,
            target=FailureTarget.GATEWAY,
            severity=1.0,
            duration_seconds=300.0,
            started_at=started,
        )
        assert s.is_expired() is False

    def test_expired_at_exact_boundary(self):
        started = datetime.now(UTC) - timedelta(seconds=300)
        s = FailureScenario(
            name="x",
            failure_type=FailureType.CRASH,
            target=FailureTarget.GATEWAY,
            severity=1.0,
            duration_seconds=300.0,
            started_at=started,
        )
        assert s.is_expired() is True

    def test_is_expired_accepts_explicit_now(self):
        """is_expired() should use the injected 'now' for deterministic tests."""
        started = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        s = FailureScenario(
            name="x",
            failure_type=FailureType.LATENCY,
            target=FailureTarget.API_SERVICE,
            severity=0.5,
            duration_seconds=60.0,
            started_at=started,
        )
        # 30 seconds later → not expired
        now_early = datetime(2024, 1, 1, 0, 0, 30, tzinfo=UTC)
        assert s.is_expired(now=now_early) is False
        # 70 seconds later → expired
        now_late = datetime(2024, 1, 1, 0, 1, 10, tzinfo=UTC)
        assert s.is_expired(now=now_late) is True


# ---------------------------------------------------------------------------
# SimulationState model
# ---------------------------------------------------------------------------


class TestSimulationState:
    def _make_scenario(self, target=FailureTarget.WORKER, active=True) -> FailureScenario:
        return FailureScenario(
            name="s",
            failure_type=FailureType.CRASH,
            target=target,
            severity=1.0,
            active=active,
        )

    def test_empty_state(self):
        state = SimulationState()
        assert state.total_active == 0
        assert state.is_healthy() is True

    def test_total_active_computed_from_active_scenarios(self):
        scenarios = [self._make_scenario(), self._make_scenario()]
        state = SimulationState(active_scenarios=scenarios)
        assert state.total_active == 2

    def test_inactive_scenarios_not_counted(self):
        active = self._make_scenario(active=True)
        inactive = self._make_scenario(active=False)
        state = SimulationState(active_scenarios=[active, inactive])
        assert state.total_active == 1

    def test_is_healthy_false_when_active_failures(self):
        state = SimulationState(active_scenarios=[self._make_scenario()])
        assert state.is_healthy() is False

    def test_active_for_target_filters_by_target(self):
        worker_s = self._make_scenario(target=FailureTarget.WORKER)
        gateway_s = self._make_scenario(target=FailureTarget.GATEWAY)
        state = SimulationState(active_scenarios=[worker_s, gateway_s])
        worker_failures = state.active_for_target(FailureTarget.WORKER)
        assert len(worker_failures) == 1
        assert worker_failures[0].target == FailureTarget.WORKER

    def test_active_for_target_includes_all_target(self):
        """Scenarios targeting ALL should appear for any target query."""
        all_s = self._make_scenario(target=FailureTarget.ALL)
        state = SimulationState(active_scenarios=[all_s])
        # Should appear for WORKER query
        assert len(state.active_for_target(FailureTarget.WORKER)) == 1
        # Should appear for GATEWAY query
        assert len(state.active_for_target(FailureTarget.GATEWAY)) == 1

    def test_snapshot_at_is_set(self):
        state = SimulationState()
        assert state.snapshot_at is not None


# ---------------------------------------------------------------------------
# InjectFailureRequest model
# ---------------------------------------------------------------------------


class TestInjectFailureRequest:
    def test_named_scenario_request(self):
        req = InjectFailureRequest(scenario_name="WORKER_CRASH")
        assert req.scenario_name == "WORKER_CRASH"

    def test_custom_failure_request(self):
        req = InjectFailureRequest(
            failure_type=FailureType.CPU_PRESSURE,
            target=FailureTarget.WORKER,
            severity=0.8,
        )
        assert req.failure_type == FailureType.CPU_PRESSURE
        assert req.target == FailureTarget.WORKER
        assert req.severity == 0.8

    def test_severity_default(self):
        req = InjectFailureRequest(scenario_name="x")
        assert req.severity == 0.7

    def test_severity_validation_fails_out_of_range(self):
        with pytest.raises(ValidationError):
            InjectFailureRequest(severity=1.5)

    def test_duration_seconds_must_be_positive(self):
        with pytest.raises(ValidationError):
            InjectFailureRequest(duration_seconds=-1.0)


# ---------------------------------------------------------------------------
# ClearFailuresRequest / Response
# ---------------------------------------------------------------------------


class TestClearFailuresModels:
    def test_clear_request_default_no_target(self):
        req = ClearFailuresRequest()
        assert req.target is None

    def test_clear_request_with_target(self):
        req = ClearFailuresRequest(target=FailureTarget.WORKER)
        assert req.target == FailureTarget.WORKER

    def test_clear_response_fields(self):
        resp = ClearFailuresResponse(cleared_count=3, message="Cleared 3 scenarios.")
        assert resp.cleared_count == 3
        assert "3" in resp.message


# ---------------------------------------------------------------------------
# ServiceHealthSnapshot model
# ---------------------------------------------------------------------------


class TestServiceHealthSnapshot:
    def test_minimal_snapshot(self):
        snap = ServiceHealthSnapshot(service_name="sim-worker", status="healthy")
        assert snap.service_name == "sim-worker"
        assert snap.status == "healthy"
        assert snap.active_failure_types == []

    def test_snapshot_with_metrics(self):
        snap = ServiceHealthSnapshot(
            service_name="sim-gateway",
            status="degraded",
            active_failure_types=["latency"],
            requests_per_second=42.5,
            error_rate_percent=5.2,
            p50_latency_ms=800.0,
            p99_latency_ms=1500.0,
            cpu_percent=12.0,
            memory_mb=75.0,
            active_connections=50,
        )
        assert snap.requests_per_second == 42.5
        assert snap.p99_latency_ms == 1500.0
        assert snap.active_connections == 50

    def test_snapshot_at_auto_set(self):
        snap = ServiceHealthSnapshot(service_name="s", status="healthy")
        assert snap.snapshot_at is not None
