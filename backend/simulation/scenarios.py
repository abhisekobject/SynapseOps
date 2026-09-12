"""
SynapseOps Simulation — Pre-defined Failure Scenarios.

This module defines the catalogue of named, reproducible failure scenarios
for the SynapseOps simulator.

Design:
- Each scenario is a factory function returning an InjectFailureRequest.
- Scenarios are registered in SCENARIO_REGISTRY (name → factory function).
- The simulation API uses this registry to look up named scenarios.
- Scenarios are documented so that operators understand what they simulate.

Phase 2 defines 10 scenarios matching the roadmap specification:
    1.  WORKER_CRASH
    2.  API_ERROR_RATE_SPIKE
    3.  DB_CONNECTION_EXHAUSTION
    4.  CPU_PRESSURE_WORKER
    5.  CASCADE_FAILURE
    6.  GATEWAY_LATENCY
    7.  MEMORY_PRESSURE_API
    8.  NETWORK_PARTITION_WORKER
    9.  REDIS_TIMEOUT
    10. DOWNSTREAM_TIMEOUT
"""

from __future__ import annotations

from backend.simulation.models import FailureTarget, FailureType, InjectFailureRequest

# ---------------------------------------------------------------------------
# Scenario factories
# ---------------------------------------------------------------------------


def scenario_worker_crash() -> InjectFailureRequest:
    """Scenario 1: Worker service crash.

    The worker service becomes completely unresponsive.
    All requests to the worker return HTTP 503.
    The job queue will begin to back up.
    Expected observable impact: queue depth rises, API response times
    increase as downstream work is not processed.
    """
    return InjectFailureRequest(
        name="WORKER_CRASH",
        failure_type=FailureType.CRASH,
        target=FailureTarget.WORKER,
        severity=1.0,
        duration_seconds=300.0,
        description=(
            "Worker service crash. All worker requests return HTTP 503. "
            "Job queue backs up. Represents a process-level failure."
        ),
    )


def scenario_api_error_rate_spike() -> InjectFailureRequest:
    """Scenario 2: API service elevated error rate.

    The API service starts returning HTTP 500 for ~40% of requests.
    The remaining requests succeed normally.
    Expected observable impact: error_rate_percent rises to ~40%,
    p99 latency is unaffected, CPU and memory are normal.
    """
    return InjectFailureRequest(
        name="API_ERROR_RATE_SPIKE",
        failure_type=FailureType.ERROR_RATE_SPIKE,
        target=FailureTarget.API_SERVICE,
        severity=0.5,  # 50% severity -> ~40% error rate (severity * 80%)
        duration_seconds=300.0,
        description=(
            "API service elevated error rate (~40% HTTP 500s). "
            "Simulates a bug or upstream dependency failure causing partial errors."
        ),
    )


def scenario_db_connection_exhaustion() -> InjectFailureRequest:
    """Scenario 3: Database connection pool exhaustion.

    The PostgreSQL connection pool is saturated. New requests that
    require a DB connection are delayed (waiting for a connection)
    and eventually fail.
    Expected observable impact: rising latency, increasing error rate
    on DB-dependent operations, connection_wait_time metric increases.
    """
    return InjectFailureRequest(
        name="DB_CONNECTION_EXHAUSTION",
        failure_type=FailureType.DB_CONNECTION_EXHAUSTION,
        target=FailureTarget.DATABASE,
        severity=0.85,
        duration_seconds=300.0,
        description=(
            "PostgreSQL connection pool exhausted. "
            "DB-dependent requests experience severe latency and begin failing. "
            "Represents pool misconfiguration or a connection leak."
        ),
    )


def scenario_cpu_pressure_worker() -> InjectFailureRequest:
    """Scenario 4: CPU pressure on worker service.

    The worker service is under heavy CPU load, causing slow job
    processing. The service is still alive but degraded.
    Expected observable impact: cpu_percent ~90%, job processing rate
    drops, queue depth rises slowly, response times increase.
    """
    return InjectFailureRequest(
        name="CPU_PRESSURE_WORKER",
        failure_type=FailureType.CPU_PRESSURE,
        target=FailureTarget.WORKER,
        severity=0.9,
        duration_seconds=300.0,
        description=(
            "Worker service under CPU pressure (~90% CPU). "
            "Job processing is slow. Service is alive but heavily degraded. "
            "Represents a CPU-intensive task or a runaway goroutine."
        ),
    )


def scenario_cascade_failure() -> InjectFailureRequest:
    """Scenario 5: Cascade failure (DB slow → worker queue backup → API latency).

    A slow database causes the worker's DB-dependent operations to take
    longer. This backs up the job queue. As the queue grows, the API's
    response times increase because background work is not completing.
    Expected observable impact: DB latency rises first, then worker queue
    depth rises, then API p99 latency rises. Classic cascade pattern.
    """
    return InjectFailureRequest(
        name="CASCADE_FAILURE",
        failure_type=FailureType.CASCADE_SLOW,
        target=FailureTarget.ALL,
        severity=0.7,
        duration_seconds=300.0,
        description=(
            "Cascade failure: DB slow → worker queue backup → API latency. "
            "Simulates the most common real-world cascade failure pattern. "
            "Root cause is DB latency; API impact is secondary."
        ),
    )


def scenario_gateway_latency() -> InjectFailureRequest:
    """Scenario 6: Gateway elevated p99 latency.

    The API gateway adds significant delay to every request it forwards.
    The upstream services are healthy; only the gateway is slow.
    Expected observable impact: p99_latency_ms rises dramatically at the
    gateway, downstream services appear normal.
    """
    return InjectFailureRequest(
        name="GATEWAY_LATENCY",
        failure_type=FailureType.LATENCY,
        target=FailureTarget.GATEWAY,
        severity=0.8,
        duration_seconds=300.0,
        description=(
            "Gateway elevated p99 latency (severity 0.8 → ~1600ms added delay). "
            "Downstream services are healthy. "
            "Represents a gateway misconfiguration or network bottleneck."
        ),
    )


def scenario_memory_pressure_api() -> InjectFailureRequest:
    """Scenario 7: API service memory pressure.

    The API service's memory usage escalates over time. The service
    remains functionally correct but is trending toward OOM.
    Expected observable impact: memory_mb metric increases steadily,
    GC pauses may cause occasional latency spikes (simulated).
    """
    return InjectFailureRequest(
        name="MEMORY_PRESSURE_API",
        failure_type=FailureType.MEMORY_PRESSURE,
        target=FailureTarget.API_SERVICE,
        severity=0.75,
        duration_seconds=300.0,
        description=(
            "API service memory pressure. Memory grows steadily toward OOM. "
            "Service is functionally correct but degrading. "
            "Represents a memory leak or unbounded cache growth."
        ),
    )


def scenario_network_partition_worker() -> InjectFailureRequest:
    """Scenario 8: Network partition — worker cannot reach database.

    The worker service cannot connect to the database (all DB calls
    time out). Worker jobs that require DB access fail.
    Expected observable impact: worker error rate spikes on DB operations,
    queue accumulates, DB-dependent jobs produce errors, health check degrades.
    """
    return InjectFailureRequest(
        name="NETWORK_PARTITION_WORKER",
        failure_type=FailureType.NETWORK_PARTITION,
        target=FailureTarget.WORKER,
        severity=1.0,
        duration_seconds=300.0,
        description=(
            "Network partition: worker cannot reach the database. "
            "All worker DB operations time out. "
            "Represents a network routing failure or firewall rule change."
        ),
    )


def scenario_redis_timeout() -> InjectFailureRequest:
    """Scenario 9: Redis connection timeouts.

    Redis operations begin timing out intermittently. Services that
    depend on Redis for caching or session state experience errors.
    Expected observable impact: cache miss rate rises, some requests
    fall back to slower code paths or fail with errors.
    """
    return InjectFailureRequest(
        name="REDIS_TIMEOUT",
        failure_type=FailureType.DOWNSTREAM_TIMEOUT,
        target=FailureTarget.REDIS,
        severity=0.6,
        duration_seconds=300.0,
        description=(
            "Redis connection timeouts (60% of Redis operations time out). "
            "Cache-dependent code paths degrade or fail. "
            "Represents Redis overload or network instability."
        ),
    )


def scenario_downstream_timeout() -> InjectFailureRequest:
    """Scenario 10: Worker downstream dependency timeout.

    The worker service makes calls to an external downstream dependency
    (simulated external API). All of these calls time out.
    Expected observable impact: worker job latency increases by the
    timeout duration, job error rate rises, throughput drops.
    """
    return InjectFailureRequest(
        name="DOWNSTREAM_TIMEOUT",
        failure_type=FailureType.DOWNSTREAM_TIMEOUT,
        target=FailureTarget.WORKER,
        severity=0.8,
        duration_seconds=300.0,
        description=(
            "Worker downstream dependency timeout. "
            "External API calls consistently time out after ~2 seconds. "
            "Represents a third-party service failure."
        ),
    )


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

#: Maps scenario name (string) to its factory function.
#: Used by the simulation API to look up named scenarios.
SCENARIO_REGISTRY: dict[str, ScenarioFactory] = {
    "WORKER_CRASH": scenario_worker_crash,
    "API_ERROR_RATE_SPIKE": scenario_api_error_rate_spike,
    "DB_CONNECTION_EXHAUSTION": scenario_db_connection_exhaustion,
    "CPU_PRESSURE_WORKER": scenario_cpu_pressure_worker,
    "CASCADE_FAILURE": scenario_cascade_failure,
    "GATEWAY_LATENCY": scenario_gateway_latency,
    "MEMORY_PRESSURE_API": scenario_memory_pressure_api,
    "NETWORK_PARTITION_WORKER": scenario_network_partition_worker,
    "REDIS_TIMEOUT": scenario_redis_timeout,
    "DOWNSTREAM_TIMEOUT": scenario_downstream_timeout,
}

# Type alias for documentation clarity
ScenarioFactory = type[InjectFailureRequest]


def get_scenario_names() -> list[str]:
    """Return a sorted list of all registered pre-defined scenario names."""
    return sorted(SCENARIO_REGISTRY.keys())


def build_scenario_request(name: str) -> InjectFailureRequest:
    """Build an InjectFailureRequest for a named pre-defined scenario.

    Args:
        name: Pre-defined scenario name (case-sensitive, e.g. 'WORKER_CRASH').

    Returns:
        InjectFailureRequest configured for the named scenario.

    Raises:
        KeyError: If the name is not in the SCENARIO_REGISTRY.
    """
    factory = SCENARIO_REGISTRY[name]
    return factory()
