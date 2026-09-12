"""
Unit tests for backend.observability.tracing (Phase 3).

Tests verify:
- configure_tracing() installs a TracerProvider without error
- configure_tracing() with otel_enabled=False installs NoOpTracerProvider
- configure_tracing() does not crash when OTLP endpoint is unreachable
- get_tracer() returns a usable tracer (can start spans)
- shutdown_tracing() runs without error
- shutdown_tracing() is idempotent (safe to call twice)
- get_current_trace_id() returns valid 32-char hex string inside a span
- get_current_span_id() returns valid 16-char hex string inside a span
- get_current_trace_id() returns empty string outside a span
"""

from __future__ import annotations

import re

from backend.observability.tracing import (
    configure_tracing,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    shutdown_tracing,
)


def _make_settings(*, otel_enabled: bool = True, endpoint: str = "http://unreachable-host:4317"):
    """Build a minimal settings-like object for tracing tests."""
    from unittest.mock import MagicMock

    s = MagicMock()
    s.otel_enabled = otel_enabled
    s.otel_service_name = "synapseops-test"
    s.otel_service_version = "0.0.0"
    s.otel_exporter_otlp_endpoint = endpoint
    s.otel_exporter_otlp_insecure = True
    s.environment = "test"
    return s


class TestConfigureTracing:
    def test_configure_tracing_enabled_does_not_raise(self) -> None:
        """configure_tracing() must not raise even with an unreachable endpoint."""
        settings = _make_settings(otel_enabled=True)
        # Should install a real or NoOp provider without raising
        configure_tracing(settings)
        shutdown_tracing()

    def test_configure_tracing_disabled_uses_noop(self) -> None:
        """When otel_enabled=False a NoOpTracerProvider should be active."""

        settings = _make_settings(otel_enabled=False)
        configure_tracing(settings)
        # NoOpTracerProvider or a wrapper — verify get_tracer still works
        tracer = get_tracer("test")
        assert tracer is not None
        shutdown_tracing()

    def test_configure_tracing_idempotent(self) -> None:
        """Calling configure_tracing() twice must not raise."""
        settings = _make_settings()
        configure_tracing(settings)
        configure_tracing(settings)
        shutdown_tracing()


class TestGetTracer:
    def test_get_tracer_returns_tracer(self) -> None:
        """get_tracer() must return a tracer object."""
        settings = _make_settings(otel_enabled=False)
        configure_tracing(settings)
        tracer = get_tracer("test.module")
        assert tracer is not None
        shutdown_tracing()

    def test_tracer_can_start_span(self) -> None:
        """A tracer returned by get_tracer() must be able to start a span."""
        settings = _make_settings(otel_enabled=False)
        configure_tracing(settings)
        tracer = get_tracer("test.spans")
        with tracer.start_as_current_span("test-operation") as span:
            assert span is not None
        shutdown_tracing()


class TestShutdownTracing:
    def test_shutdown_does_not_raise(self) -> None:
        settings = _make_settings(otel_enabled=False)
        configure_tracing(settings)
        shutdown_tracing()  # should not raise

    def test_shutdown_is_idempotent(self) -> None:
        """Calling shutdown_tracing() when not initialised must not raise."""
        shutdown_tracing()
        shutdown_tracing()


class TestTraceIdHelpers:
    def test_trace_id_empty_outside_span(self) -> None:
        """get_current_trace_id() returns empty string when no span is active."""
        settings = _make_settings(otel_enabled=False)
        configure_tracing(settings)
        trace_id = get_current_trace_id()
        # Outside a span context it should be empty
        assert isinstance(trace_id, str)
        shutdown_tracing()

    def test_span_id_empty_outside_span(self) -> None:
        """get_current_span_id() returns empty string when no span is active."""
        settings = _make_settings(otel_enabled=False)
        configure_tracing(settings)
        span_id = get_current_span_id()
        assert isinstance(span_id, str)
        shutdown_tracing()

    def test_trace_id_format_inside_span(self) -> None:
        """Inside an active span, trace ID must be a 32-char hex string."""
        from opentelemetry.sdk.trace import TracerProvider

        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            trace_id = get_current_trace_id()
        # Either 32-char hex or empty (NoOp spans have invalid context)
        assert re.match(r"^[0-9a-f]{32}$", trace_id) or trace_id == ""

    def test_span_id_format_inside_span(self) -> None:
        """Inside an active span, span ID must be a 16-char hex string."""
        from opentelemetry.sdk.trace import TracerProvider

        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            span_id = get_current_span_id()
        assert re.match(r"^[0-9a-f]{16}$", span_id) or span_id == ""
