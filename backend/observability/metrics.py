"""
SynapseOps Observability — Prometheus Metrics (Phase 3).

Provides prometheus_client instrumentation for the main SynapseOps API.

Metric taxonomy:
    synapseops_http_requests_total          Counter   (service, method, route, status_code)
    synapseops_http_request_duration_seconds Histogram (service, method, route)
    synapseops_http_requests_in_flight      Gauge     (service)
    synapseops_active_failures_total        Gauge     (no labels -- low cardinality)
    synapseops_info                         Info      (service identity)

Label design:
    - `service`     : stable service name (e.g. "synapseops-api")
    - `method`      : HTTP method (GET, POST, etc.)
    - `route`       : normalised FastAPI route template (e.g. "/health/live")
    - `status_code` : HTTP status as string ("200", "500", etc.)

High-cardinality values (user IDs, request bodies, raw URLs, timestamps)
are NEVER used as labels.

Design notes:
    - Uses a dedicated CollectorRegistry to avoid clashing with the default
      prometheus_client registry (which includes Python process metrics).
    - All metric objects are module-level singletons; safe to import from
      anywhere in the application.
    - If the prometheus_client package is somehow unavailable at import time
      (defensive) get_metrics_output() returns an empty string rather than
      crashing the application.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# ---------------------------------------------------------------------------
# Dedicated registry — avoids polluting / colliding with default registry
# ---------------------------------------------------------------------------
REGISTRY = CollectorRegistry(auto_describe=True)

# ---------------------------------------------------------------------------
# Service identity label (constant for this process)
# ---------------------------------------------------------------------------
SERVICE_NAME = "synapseops-api"

_SERVICE_INFO = Info(
    "synapseops",
    "SynapseOps service identity",
    registry=REGISTRY,
)
_SERVICE_INFO.info({"service": SERVICE_NAME, "phase": "3"})

# ---------------------------------------------------------------------------
# HTTP metrics
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "synapseops_http_requests_total",
    "Total HTTP requests handled by the SynapseOps API",
    labelnames=["service", "method", "route", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION = Histogram(
    "synapseops_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["service", "method", "route"],
    # Buckets tuned for an API service: 1ms - 10s
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "synapseops_http_requests_in_flight",
    "Number of HTTP requests currently being processed",
    labelnames=["service"],
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Simulation state metrics
# ---------------------------------------------------------------------------

ACTIVE_FAILURES_TOTAL = Gauge(
    "synapseops_active_failures_total",
    "Number of currently active failure scenarios in the simulation",
    registry=REGISTRY,
)


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------


def get_metrics_output() -> str:
    """Return the Prometheus text-format metrics string.

    Uses the dedicated SynapseOps registry only.
    Returns an empty string if serialisation fails (fail-safe).
    """
    try:
        return generate_latest(REGISTRY).decode("utf-8")
    except Exception:
        return ""


def record_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record a completed HTTP request into all relevant metrics.

    Args:
        method: HTTP method string (e.g. "GET").
        route: Normalised FastAPI route template (e.g. "/health/live").
               Use the template, not the raw URL, to avoid high cardinality.
        status_code: HTTP response status code integer.
        duration_seconds: Request duration in seconds.
    """
    labels = {
        "service": SERVICE_NAME,
        "method": method.upper(),
        "route": route,
        "status_code": str(status_code),
    }
    HTTP_REQUESTS_TOTAL.labels(**labels).inc()
    HTTP_REQUEST_DURATION.labels(service=SERVICE_NAME, method=method.upper(), route=route).observe(
        duration_seconds
    )


def update_active_failures(count: int) -> None:
    """Update the active failures gauge.

    Called from the simulation controller or middleware after each
    failure injection / clear operation.
    """
    ACTIVE_FAILURES_TOTAL.set(count)
