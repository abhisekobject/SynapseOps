"""
SynapseOps Observability Package — Phase 3.

Provides the observability foundation:
- metrics: prometheus_client instrumentation for the main API
- tracing: OpenTelemetry SDK setup with OTLP gRPC export
- middleware: request correlation ID + Prometheus metrics recording
"""
