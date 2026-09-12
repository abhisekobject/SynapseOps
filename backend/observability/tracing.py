"""
SynapseOps Observability -- Distributed Tracing (Phase 3).

Initialises the OpenTelemetry SDK with an OTLP gRPC exporter targeting
the local Jaeger all-in-one instance (or any OTLP-compatible backend).

Architecture:
    Application code calls get_tracer(name) to obtain a named Tracer.
    The TracerProvider sends completed spans to Jaeger via gRPC.
    W3C TraceContext headers are used for cross-service propagation.

Fail-safe design:
    If the OTLP exporter endpoint is unreachable or SDK initialisation
    raises for any reason, configure_tracing() installs a NoOpTracerProvider
    instead of propagating the error.  Application behaviour is unaffected.

Standard OTel env vars (honoured automatically by the SDK):
    OTEL_SERVICE_NAME               -- service name label
    OTEL_EXPORTER_OTLP_ENDPOINT    -- gRPC endpoint (e.g. http://jaeger:4317)
    OTEL_RESOURCE_ATTRIBUTES        -- key=value pairs for resource attributes

Usage:
    # At application startup:
    configure_tracing(settings)

    # In any module:
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("key", "value")
        ...

    # At application shutdown:
    shutdown_tracing()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import NoOpTracerProvider

if TYPE_CHECKING:
    from backend.core.config import Settings

_logger = logging.getLogger(__name__)

# Module-level reference to the active provider (for shutdown)
_provider: TracerProvider | None = None


def configure_tracing(settings: Settings) -> None:
    """Initialise the global OpenTelemetry TracerProvider.

    Should be called once at application startup, before any request
    handling begins.

    Args:
        settings: Application settings (provides OTel endpoint, service name,
                  version, and environment).
    """
    global _provider

    if not settings.otel_enabled:
        _logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=false)")
        trace.set_tracer_provider(NoOpTracerProvider())
        return

    try:
        resource = Resource.create(
            {
                SERVICE_NAME: settings.otel_service_name,
                SERVICE_VERSION: settings.otel_service_version,
                "deployment.environment": settings.environment,
            }
        )

        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=settings.otel_exporter_otlp_insecure,
        )

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _provider = provider

        _logger.info(
            "OpenTelemetry tracing configured",
            extra={
                "service": settings.otel_service_name,
                "endpoint": settings.otel_exporter_otlp_endpoint,
            },
        )

    except Exception as exc:
        # Telemetry must not crash the application.
        _logger.warning(
            "OpenTelemetry tracing setup failed; using NoOpTracerProvider. "
            "Application will continue without tracing. Error: %s",
            exc,
        )
        trace.set_tracer_provider(NoOpTracerProvider())


def get_tracer(name: str) -> trace.Tracer:
    """Return a named tracer from the active TracerProvider.

    Args:
        name: Instrumentation scope name; typically ``__name__`` of the
              calling module.

    Returns:
        A Tracer instance.  If tracing is disabled or failed to initialise
        this will be a no-op tracer -- safe to use without checking.
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush and shut down the TracerProvider.

    Should be called during application shutdown to ensure all buffered
    spans are exported before the process exits.
    """
    global _provider
    if _provider is not None:
        try:
            _provider.shutdown()
        except Exception as exc:
            _logger.warning("Error shutting down TracerProvider: %s", exc)
        finally:
            _provider = None


def get_current_trace_id() -> str:
    """Return the current trace ID as a 32-hex-character string, or empty string.

    Useful for injecting into structured log records.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return ""


def get_current_span_id() -> str:
    """Return the current span ID as a 16-hex-character string, or empty string."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.span_id, "016x")
    return ""
