# System State & Event Intelligence (Phase 4)

## Objective
Phase 4 transforms raw telemetry into a structured, coherent representation of the infrastructure system. It bridges the gap between passive observation (Phase 3) and anomaly detection (Phase 5). 

This layer answers:
- Which services exist?
- What is their current operational state?
- What operational events have recently occurred?

## Telemetry vs Events vs State

1. **Telemetry**: Raw, instantaneous observations (e.g., `latency_p99 = 850ms`).
2. **Event**: A normalized operational occurrence derived from telemetry using deterministic rules (e.g., `LATENCY_INCREASE`, severity: `WARNING`).
3. **State**: The current aggregated operational condition of an entity (e.g., `DEGRADED`, based on active events).

## Architecture

```text
                  ┌─────────────────────┐
                  │ Infrastructure      │
                  │ Simulation          │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Phase 3             │
                  │ Observability       │
                  └──────────┬──────────┘
                             │
                       Raw Telemetry
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Telemetry           │
                  │ Normalizer          │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Event Engine        │
                  │ + Deduplication     │
                  │ + Correlation       │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ System State Engine │
                  └──────────┬──────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
        Current System State      Event History
                 │                       │
                 └───────────┬───────────┘
                             ▼
                       Phase 5
                  Anomaly Detection
```

## Deterministic Thresholds
Events are generated strictly using threshold rules defined in `config.py`. 
- **Latency**: Warning > 300ms, Critical > 800ms
- **Error Rate**: Warning > 1%, Critical > 5%
- **Queue Depth**: Warning > 10, Critical > 30

## Deduplication Strategy
The `EventEngine` deduplicates incoming events using a `correlation_id` (typically `{service_id}::{event_type}`). 
If a condition persists across polling cycles, the existing active event's `updated_at` and `evidence` are updated rather than creating thousands of duplicate records.

## State Transitions
The `SystemStateEngine` computes a deterministic state based on the active events:
- No active warnings/criticals: `HEALTHY`
- Active warnings or non-unavailable criticals: `DEGRADED`
- Active `SERVICE_UNAVAILABLE`: `UNAVAILABLE`

## Stale-State Policy
If telemetry for a service is missing for longer than `STATE_STALENESS_SECONDS` (default: 15s), the service's state is transitioned to `UNKNOWN`. We do not silently infer health from an absence of data.

## API Endpoints
- `GET /api/v1/state`: Returns the overall `SystemSnapshot`.
- `GET /api/v1/events/active`: Returns all currently active operational events.

## Phase Boundary
Phase 4 explicitly **does not** include:
- Machine Learning / Statistical Anomaly Detection (Phase 5)
- Dependency Graph / Root Cause Analysis (Phase 6)
- LLM Reasoning (Phase 7)
- Automated Recovery (Phase 8/10)
