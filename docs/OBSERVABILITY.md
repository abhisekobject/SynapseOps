# SynapseOps — Observability & Telemetry (Phase 3)

> **Status**: COMPLETE  
> **Phase**: 3 of N  
> **Core loop stage**: **OBSERVE**

---

## Overview

Phase 3 adds production-grade observability to every layer of SynapseOps:

| Pillar | Technology | What is instrumented |
|---|---|---|
| Metrics | Prometheus + prometheus-client | Main API, all simulated services |
| Tracing | OpenTelemetry SDK → Jaeger | Main API + simulated services (A+A) |
| Request correlation | UUID v4 `X-Request-ID` | All HTTP requests across all services |
| Structured logging | structlog + OTel context injection | All application code |

---

## Architecture

```
Browser / curl
    │
    ▼
SynapseOps API (:8000)
 ├── RequestCorrelationMiddleware
 │     ├── Reads/generates X-Request-ID
 │     ├── Increments/decrements in-flight gauge
 │     └── Calls record_request() on response
 ├── GET /metrics          → Prometheus text format
 └── OTel SDK → BatchSpanProcessor
                    └── OTLPSpanExporter (gRPC)
                              └── Jaeger (:4317)

Simulated Services (:8100-8102)
 ├── Hand-rolled /metrics   (Phase 2 preserved)
 └── FastAPIInstrumentor    (Phase 3 added: A+A)
          └── OTLPSpanExporter → Jaeger

Prometheus (:9090)  scrapes all /metrics endpoints every 15s
Grafana (:3000)     queries Prometheus, shows pre-built dashboard
Jaeger (:16686)     receives OTLP spans, shows distributed traces
```

---

## Accessing the Observability Stack

Once `docker compose up -d` is running:

| UI | URL | Credentials |
|---|---|---|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Jaeger | http://localhost:16686 | — |
| Raw metrics (API) | http://localhost:8000/metrics | — |
| Raw metrics (gateway) | http://localhost:8100/metrics | — |

---

## Metrics Reference

All metrics use the `synapseops_` prefix and live in a **dedicated Prometheus registry** (not the default global one).

### Main API Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `synapseops_http_requests_total` | Counter | service, method, route, status_code | Total HTTP requests served |
| `synapseops_http_request_duration_seconds` | Histogram | service, method, route | Request latency (buckets: 1ms–10s) |
| `synapseops_http_requests_in_flight` | Gauge | service | Requests currently being processed |
| `synapseops_active_failures_total` | Gauge | — | Count of currently active failure scenarios |
| `synapseops_info` | Info | version, environment | Service identity label |

### Simulated Service Metrics (hand-rolled, Phase 2)

Each service (`gateway`, `api`, `worker`) exposes at `/metrics`:

```
sim_{service}_requests_per_second
sim_{service}_error_rate_percent
sim_{service}_request_latency_p99_ms
sim_{service}_cpu_percent
sim_{service}_memory_mb
sim_{service}_healthy
sim_worker_queue_depth   # worker only
```

---

## Distributed Tracing

### Configuration

| Env var | Default | Description |
|---|---|---|
| `OTEL_ENABLED` | `true` | Enable/disable OTel tracing |
| `OTEL_SERVICE_NAME` | `synapseops-api` | Service identity in Jaeger |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Jaeger gRPC endpoint |
| `OTEL_EXPORTER_OTLP_INSECURE` | `true` | Use plaintext gRPC |

### Fail-safe behaviour

OTel initialisation failures **never crash the application**. If the Jaeger endpoint is unreachable at startup, a `NoOpTracerProvider` is installed automatically. All tracing calls become no-ops — the application continues operating normally.

### Using the tracer in application code

```python
from backend.observability.tracing import get_tracer

tracer = get_tracer(__name__)


async def my_handler():
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("key", "value")
        result = await do_work()
    return result
```

---

## Request Correlation

Every HTTP request receives a `X-Request-ID` header:

- If the client sends `X-Request-ID`, that value is preserved and echoed back.
- If absent, a UUID v4 is generated.
- The ID is bound to the structlog context — **all log lines emitted during a request include `request_id`**.
- The ID is returned in the response `X-Request-ID` header.
- The current OTel `trace_id` is also injected into log records when a span is active.

---

## Grafana Dashboard

The pre-provisioned **SynapseOps — Infrastructure Overview** dashboard (`observability/grafana/dashboards/synapseops_overview.json`) shows:

- Request rate (req/s) per service
- Error rate (%) per service  
- p99 request latency (ms) per service
- Worker queue depth
- Service health status (healthy / degraded)
- Active failure scenario count
- CPU utilisation per service

---

## Running Without Docker

Set `OTEL_ENABLED=false` to disable tracing when running locally without Jaeger. Prometheus metrics at `/metrics` work without any external dependencies.

```bash
OTEL_ENABLED=false uvicorn backend.main:app --reload
```
