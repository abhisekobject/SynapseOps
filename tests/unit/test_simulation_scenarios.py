"""
Unit tests — Pre-defined Failure Scenarios.

Tests that all 10 pre-defined scenarios are correctly defined, registered,
and produce valid InjectFailureRequest objects. No external dependencies required.
"""

from __future__ import annotations

import pytest

from backend.simulation.models import FailureTarget, FailureType, InjectFailureRequest
from backend.simulation.scenarios import (
    SCENARIO_REGISTRY,
    build_scenario_request,
    get_scenario_names,
    scenario_api_error_rate_spike,
    scenario_cascade_failure,
    scenario_cpu_pressure_worker,
    scenario_db_connection_exhaustion,
    scenario_downstream_timeout,
    scenario_gateway_latency,
    scenario_memory_pressure_api,
    scenario_network_partition_worker,
    scenario_redis_timeout,
    scenario_worker_crash,
)

# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


class TestScenarioRegistry:
    def test_registry_has_ten_scenarios(self):
        assert len(SCENARIO_REGISTRY) == 10

    def test_all_expected_names_in_registry(self):
        expected = {
            "WORKER_CRASH",
            "API_ERROR_RATE_SPIKE",
            "DB_CONNECTION_EXHAUSTION",
            "CPU_PRESSURE_WORKER",
            "CASCADE_FAILURE",
            "GATEWAY_LATENCY",
            "MEMORY_PRESSURE_API",
            "NETWORK_PARTITION_WORKER",
            "REDIS_TIMEOUT",
            "DOWNSTREAM_TIMEOUT",
        }
        assert set(SCENARIO_REGISTRY.keys()) == expected

    def test_get_scenario_names_returns_sorted_list(self):
        names = get_scenario_names()
        assert names == sorted(names)
        assert len(names) == 10

    def test_build_scenario_request_returns_inject_request(self):
        for name in SCENARIO_REGISTRY:
            req = build_scenario_request(name)
            assert isinstance(req, InjectFailureRequest), f"Failed for scenario: {name}"

    def test_build_scenario_request_raises_on_unknown_name(self):
        with pytest.raises(KeyError):
            build_scenario_request("NONEXISTENT_SCENARIO")


# ---------------------------------------------------------------------------
# Individual scenario validation
# ---------------------------------------------------------------------------


class TestWorkerCrash:
    def test_creates_valid_request(self):
        req = scenario_worker_crash()
        assert isinstance(req, InjectFailureRequest)

    def test_targets_worker(self):
        req = scenario_worker_crash()
        assert req.target == FailureTarget.WORKER

    def test_failure_type_is_crash(self):
        req = scenario_worker_crash()
        assert req.failure_type == FailureType.CRASH

    def test_severity_is_maximum(self):
        req = scenario_worker_crash()
        assert req.severity == 1.0

    def test_has_description(self):
        req = scenario_worker_crash()
        assert len(req.description) > 0

    def test_name_is_correct(self):
        req = scenario_worker_crash()
        assert req.name == "WORKER_CRASH"


class TestApiErrorRateSpike:
    def test_targets_api_service(self):
        req = scenario_api_error_rate_spike()
        assert req.target == FailureTarget.API_SERVICE

    def test_failure_type_is_error_rate_spike(self):
        req = scenario_api_error_rate_spike()
        assert req.failure_type == FailureType.ERROR_RATE_SPIKE

    def test_severity_in_valid_range(self):
        req = scenario_api_error_rate_spike()
        assert 0.0 <= req.severity <= 1.0


class TestDbConnectionExhaustion:
    def test_targets_database(self):
        req = scenario_db_connection_exhaustion()
        assert req.target == FailureTarget.DATABASE

    def test_failure_type_is_db_exhaustion(self):
        req = scenario_db_connection_exhaustion()
        assert req.failure_type == FailureType.DB_CONNECTION_EXHAUSTION


class TestCpuPressureWorker:
    def test_targets_worker(self):
        req = scenario_cpu_pressure_worker()
        assert req.target == FailureTarget.WORKER

    def test_failure_type_is_cpu_pressure(self):
        req = scenario_cpu_pressure_worker()
        assert req.failure_type == FailureType.CPU_PRESSURE

    def test_severity_is_high(self):
        req = scenario_cpu_pressure_worker()
        assert req.severity >= 0.8  # CPU pressure should be severe


class TestCascadeFailure:
    def test_targets_all(self):
        req = scenario_cascade_failure()
        assert req.target == FailureTarget.ALL

    def test_failure_type_is_cascade_slow(self):
        req = scenario_cascade_failure()
        assert req.failure_type == FailureType.CASCADE_SLOW


class TestGatewayLatency:
    def test_targets_gateway(self):
        req = scenario_gateway_latency()
        assert req.target == FailureTarget.GATEWAY

    def test_failure_type_is_latency(self):
        req = scenario_gateway_latency()
        assert req.failure_type == FailureType.LATENCY


class TestMemoryPressureApi:
    def test_targets_api_service(self):
        req = scenario_memory_pressure_api()
        assert req.target == FailureTarget.API_SERVICE

    def test_failure_type_is_memory_pressure(self):
        req = scenario_memory_pressure_api()
        assert req.failure_type == FailureType.MEMORY_PRESSURE


class TestNetworkPartitionWorker:
    def test_targets_worker(self):
        req = scenario_network_partition_worker()
        assert req.target == FailureTarget.WORKER

    def test_failure_type_is_network_partition(self):
        req = scenario_network_partition_worker()
        assert req.failure_type == FailureType.NETWORK_PARTITION

    def test_severity_is_maximum(self):
        req = scenario_network_partition_worker()
        assert req.severity == 1.0


class TestRedisTimeout:
    def test_targets_redis(self):
        req = scenario_redis_timeout()
        assert req.target == FailureTarget.REDIS

    def test_failure_type_is_downstream_timeout(self):
        req = scenario_redis_timeout()
        assert req.failure_type == FailureType.DOWNSTREAM_TIMEOUT


class TestDownstreamTimeout:
    def test_targets_worker(self):
        req = scenario_downstream_timeout()
        assert req.target == FailureTarget.WORKER

    def test_failure_type_is_downstream_timeout(self):
        req = scenario_downstream_timeout()
        assert req.failure_type == FailureType.DOWNSTREAM_TIMEOUT


# ---------------------------------------------------------------------------
# Cross-scenario invariants
# ---------------------------------------------------------------------------


class TestScenarioInvariants:
    def test_all_scenarios_have_positive_severity(self):
        for name in SCENARIO_REGISTRY:
            req = build_scenario_request(name)
            assert req.severity > 0.0, f"Scenario {name} has zero severity"

    def test_all_scenarios_have_valid_severity(self):
        for name in SCENARIO_REGISTRY:
            req = build_scenario_request(name)
            assert 0.0 <= req.severity <= 1.0, f"Scenario {name} has out-of-range severity"

    def test_all_scenarios_have_non_empty_description(self):
        for name in SCENARIO_REGISTRY:
            req = build_scenario_request(name)
            assert req.description, f"Scenario {name} has no description"

    def test_all_scenarios_have_non_empty_name(self):
        for name in SCENARIO_REGISTRY:
            req = build_scenario_request(name)
            assert req.name, f"Scenario {name} has no name field"

    def test_all_scenarios_have_positive_duration(self):
        for name in SCENARIO_REGISTRY:
            req = build_scenario_request(name)
            if req.duration_seconds is not None:
                assert req.duration_seconds > 0, f"Scenario {name} has non-positive duration"

    def test_scenario_names_match_registry_keys(self):
        """Each scenario's name field should match the registry key it's stored under."""
        for registry_key in SCENARIO_REGISTRY:
            req = build_scenario_request(registry_key)
            assert req.name == registry_key, (
                f"Registry key '{registry_key}' != scenario name '{req.name}'"
            )
