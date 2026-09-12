"""
Unit tests for backend.observability.metrics (Phase 3).

Tests verify:
- Registry is isolated (not the default prometheus_client registry)
- Expected metrics exist with correct names/types
- counter increments correctly
- histogram records observations
- gauge increments/decrements correctly
- label values are bounded (no high-cardinality leakage)
- get_metrics_output() returns valid Prometheus text format
- service identity label is correct
- update_active_failures() sets the gauge correctly
"""

from __future__ import annotations

from backend.observability.metrics import (
    ACTIVE_FAILURES_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_IN_FLIGHT,
    HTTP_REQUESTS_TOTAL,
    REGISTRY,
    SERVICE_NAME,
    get_metrics_output,
    record_request,
    update_active_failures,
)

# ---------------------------------------------------------------------------
# Registry / identity tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_registry_is_not_default(self) -> None:
        """The SynapseOps registry must be a dedicated instance."""
        from prometheus_client import REGISTRY as DEFAULT

        assert REGISTRY is not DEFAULT

    def test_service_name_constant(self) -> None:
        """SERVICE_NAME must be the canonical main-API identifier."""
        assert SERVICE_NAME == "synapseops-api"

    def test_metrics_output_is_non_empty(self) -> None:
        """get_metrics_output() must return a non-empty string."""
        output = get_metrics_output()
        assert isinstance(output, str)
        assert len(output) > 0

    def test_metrics_output_contains_service_info(self) -> None:
        """Output must include the synapseops_info metric."""
        output = get_metrics_output()
        assert "synapseops_info" in output

    def test_metrics_output_prometheus_format(self) -> None:
        """Output must contain HELP and TYPE lines (valid Prometheus format)."""
        output = get_metrics_output()
        assert "# HELP" in output
        assert "# TYPE" in output


# ---------------------------------------------------------------------------
# HTTP counter tests
# ---------------------------------------------------------------------------


class TestHttpRequestsTotal:
    def test_counter_increments_on_record_request(self) -> None:
        """record_request() must increment the counter."""
        # Read current value
        before = HTTP_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME, method="GET", route="/test-counter", status_code="200"
        )._value.get()

        record_request(
            method="GET",
            route="/test-counter",
            status_code=200,
            duration_seconds=0.05,
        )

        after = HTTP_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME, method="GET", route="/test-counter", status_code="200"
        )._value.get()

        assert after == before + 1

    def test_counter_uses_string_status_code(self) -> None:
        """Status code label must be a string to keep cardinality bounded."""
        record_request(
            method="POST",
            route="/test-string-status",
            status_code=404,
            duration_seconds=0.01,
        )
        # Verify the label was stored as string "404"
        val = HTTP_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            method="POST",
            route="/test-string-status",
            status_code="404",
        )._value.get()
        assert val >= 1

    def test_counter_method_uppercased(self) -> None:
        """HTTP method labels must be upper-cased."""
        record_request(
            method="get",  # lower-case input
            route="/test-uppercase",
            status_code=200,
            duration_seconds=0.01,
        )
        val = HTTP_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            method="GET",  # must be stored upper-case
            route="/test-uppercase",
            status_code="200",
        )._value.get()
        assert val >= 1


# ---------------------------------------------------------------------------
# Histogram tests
# ---------------------------------------------------------------------------


class TestHttpRequestDuration:
    def test_histogram_records_observation(self) -> None:
        """record_request() must record a histogram observation."""
        before_count = HTTP_REQUEST_DURATION.labels(
            service=SERVICE_NAME, method="GET", route="/hist-test"
        )._sum.get()

        record_request(
            method="GET",
            route="/hist-test",
            status_code=200,
            duration_seconds=0.123,
        )

        after_count = HTTP_REQUEST_DURATION.labels(
            service=SERVICE_NAME, method="GET", route="/hist-test"
        )._sum.get()

        assert after_count > before_count

    def test_histogram_sum_approximately_correct(self) -> None:
        """Histogram sum must reflect the observed duration."""
        before = HTTP_REQUEST_DURATION.labels(
            service=SERVICE_NAME, method="PUT", route="/sum-test"
        )._sum.get()

        record_request(method="PUT", route="/sum-test", status_code=201, duration_seconds=0.5)

        after = HTTP_REQUEST_DURATION.labels(
            service=SERVICE_NAME, method="PUT", route="/sum-test"
        )._sum.get()

        assert abs((after - before) - 0.5) < 0.001


# ---------------------------------------------------------------------------
# Gauge tests
# ---------------------------------------------------------------------------


class TestInFlightGauge:
    def test_gauge_increments(self) -> None:
        before = HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME)._value.get()
        HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME).inc()
        after = HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME)._value.get()
        assert after == before + 1
        # Clean up
        HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME).dec()

    def test_gauge_decrements(self) -> None:
        HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME).inc()
        before = HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME)._value.get()
        HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME).dec()
        after = HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME)._value.get()
        assert after == before - 1


class TestActiveFailuresGauge:
    def test_update_sets_gauge(self) -> None:
        update_active_failures(3)
        val = ACTIVE_FAILURES_TOTAL._value.get()
        assert val == 3.0

    def test_update_to_zero(self) -> None:
        update_active_failures(0)
        val = ACTIVE_FAILURES_TOTAL._value.get()
        assert val == 0.0


# ---------------------------------------------------------------------------
# Output content tests
# ---------------------------------------------------------------------------


class TestMetricsOutput:
    def test_output_contains_expected_metric_names(self) -> None:
        output = get_metrics_output()
        expected = [
            "synapseops_http_requests_total",
            "synapseops_http_request_duration_seconds",
            "synapseops_http_requests_in_flight",
            "synapseops_active_failures_total",
        ]
        for name in expected:
            assert name in output, f"Missing metric: {name}"

    def test_get_metrics_output_is_fail_safe(self) -> None:
        """get_metrics_output() must return a string even if called twice rapidly."""
        out1 = get_metrics_output()
        out2 = get_metrics_output()
        assert isinstance(out1, str)
        assert isinstance(out2, str)
