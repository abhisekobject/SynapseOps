# System Architecture — SynapseOps

> **Status**: Intended target architecture — documented as a design goal. Components described here have not yet been implemented.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The Operational Loop](#2-the-operational-loop)
3. [Layer-by-Layer Description](#3-layer-by-layer-description)
4. [Component Specifications](#4-component-specifications)
5. [Data Flow Summary](#5-data-flow-summary)
6. [Target Repository Structure](#6-target-repository-structure)
7. [Architecture Evolution Strategy](#7-architecture-evolution-strategy)

---

## 1. Architecture Overview

```
                    SYNAPSEOPS
                         │
                         ▼
              ┌────────────────────┐
              │   Observability    │
              │  Metrics / Logs /  │
              │  Traces / Events   │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Event & State     │
              │  Intelligence      │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Detection &       │
              │  Anomaly Analysis  │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Dependency &      │
              │  Root Cause        │
              │  Reasoning         │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  AI Incident       │
              │  Reasoning         │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Recovery Planning │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Safety & Policy   │
              └─────────┬──────────┘
                        │
                 ┌──────┴──────┐
                 ▼             ▼
             Automatic    Human Approval
             Execution        Queue
                 │             │
                 └──────┬──────┘
                        ▼
              ┌────────────────────┐
              │  Action Executor   │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Verification &    │
              │  Outcome Analysis  │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Feedback/Learning │
              └─────────┬──────────┘
                        │
                        └──────────→ OBSERVE AGAIN
```

---

## 2. The Operational Loop

The architecture is organized around a closed-loop cycle. Each iteration of this loop processes an incident from initial detection through to outcome recording:

```
OBSERVE     →  Collect telemetry from infrastructure
DETECT      →  Identify anomalous signals
UNDERSTAND  →  Build system state model and dependency graph
DIAGNOSE    →  Generate root cause hypotheses
REASON      →  Synthesize evidence into structured incident understanding
PLAN        →  Propose candidate recovery actions
SAFETY      →  Evaluate actions against policy; apply risk assessment
ACT         →  Execute authorized actions (or await human approval)
VERIFY      →  Observe environment to confirm recovery
LEARN       →  Record outcome; update models and preferences
(return to OBSERVE)
```

This loop is not a strict sequential pipeline. In practice, some stages will run continuously (observation), some will run reactively (detection), and some will run per-incident (diagnosis, planning, execution, verification).

---

## 3. Layer-by-Layer Description

### Layer 1: Observability

**Purpose**: Ingest and normalize telemetry from the target infrastructure.

The observability layer collects:
- Time-series **metrics** (CPU, memory, latency, error rate, saturation, queue depths)
- Structured **logs** from application components
- Distributed **traces** showing cross-service request paths
- Discrete **events** (deployments, restarts, health-check changes, scaling events)

This layer is concerned with collection and normalization, not analysis. Its output is a normalized, time-indexed stream of operational signals.

Technologies: Prometheus (metrics), OpenTelemetry (instrumentation), Loki (logs — conditional), structured log ingestion.

---

### Layer 2: Event & State Intelligence

**Purpose**: Transform raw telemetry into a structured model of current system state.

This layer maintains:
- Current health status of each service and infrastructure component
- Aggregated metric snapshots
- Recent event history
- Detected state transitions (healthy → degraded → failing)
- Correlation windows for grouping related signals

The output of this layer is a queryable **system state model** — a representation of "what is currently happening" in the infrastructure.

---

### Layer 3: Detection & Anomaly Analysis

**Purpose**: Identify signals that deviate significantly from expected behavior.

Detection approaches will include:
- Statistical baseline modeling (moving averages, standard deviation bands)
- ML-based anomaly detection (isolation forests, time-series models)
- Rule-based threshold detection for well-understood failure modes
- Pattern detection in log streams

The output of this layer is a set of **detected anomalies** with associated evidence, severity estimates, and affected components. Anomaly detection does not perform diagnosis — it identifies that something unusual is occurring.

---

### Layer 4: Dependency & Root Cause Reasoning

**Purpose**: Use service dependency topology to trace failure propagation and identify probable root causes.

This layer:
- Maintains a **dependency graph** of all known infrastructure relationships
- Propagates anomaly signals through the graph to identify upstream/downstream effects
- Applies graph-based reasoning to distinguish root causes from downstream symptoms
- Generates **root cause hypotheses** with supporting evidence

The output is a ranked list of probable root causes with confidence estimates.

Technologies: NetworkX initially; a dedicated graph database if requirements warrant it.

---

### Layer 5: AI Incident Reasoning

**Purpose**: Synthesize evidence, dependency analysis, and historical context into structured incident understanding.

This layer may use:
- LLM-based reasoning to interpret complex, multimodal evidence
- Structured prompting to generate hypotheses and explanations
- Retrieval-augmented generation over historical incident records
- Confidence-scored output that feeds the recovery planning layer

**Critical constraint**: This layer produces structured output conforming to a defined schema. It does not directly access execution APIs. Its output is validated before proceeding to planning.

---

### Layer 6: Recovery Planning

**Purpose**: Generate a ranked list of candidate recovery actions for the detected incident.

This layer:
- Maps incident hypotheses to known recovery action types
- Considers system state, dependency effects, and action prerequisites
- Estimates risk level and expected effectiveness of each candidate action
- Produces a structured **recovery plan** with ranked action candidates

---

### Layer 7: Safety & Policy Engine

**Purpose**: Evaluate every proposed action against defined policies before any execution occurs.

This layer:
- Applies risk classification to each proposed action
- Checks authorization rules (is this action permitted in this context?)
- Determines whether the action can be executed autonomously or requires human approval
- Routes high-risk actions to the human approval queue
- Enforces rate limits, scope limits, and action preconditions

This layer is entirely deterministic. It does not use AI/ML.

---

### Layer 8: Action Executor

**Purpose**: Execute authorized recovery actions against the target infrastructure.

The executor:
- Receives a validated, authorized action specification
- Executes the action through the appropriate infrastructure API
- Records the execution result (success, failure, timeout)
- Does not interpret, modify, or augment the action specification

The executor is intentionally simple and bounded. It is the last engineered safeguard before infrastructure modification occurs.

---

### Layer 9: Verification & Outcome Analysis

**Purpose**: Confirm that the executed action achieved the intended system recovery.

After execution, the verification layer:
- Waits for a configurable observation window
- Re-samples relevant telemetry
- Compares observed state to the expected healthy baseline
- Produces a binary or graded recovery confirmation
- Triggers escalation or rollback if recovery is not confirmed

This layer enforces the distinction between "action succeeded" and "system recovered."

---

### Layer 10: Feedback & Learning

**Purpose**: Record outcomes and update system models to improve future decisions.

This layer:
- Persists all incident records, hypotheses, actions, and outcomes
- Updates anomaly detection baselines
- Records operator feedback and corrections
- Over time, informs recovery planning with historical effectiveness data

This layer is the foundation of the system's capacity to improve over time.

---

### Supporting Layer: Dashboard & Operator Interface

**Purpose**: Provide human operators with visibility into the system's state and decisions.

The dashboard:
- Displays current infrastructure health
- Shows active incidents with evidence and hypotheses
- Presents recovery plans pending human approval
- Shows execution and verification results
- Provides historical incident and outcome records

The dashboard is an interface, not the intelligence. It exists to make the underlying operational loop visible and governable by human operators.

---

## 4. Component Specifications

Detailed component specifications (inputs, outputs, responsibilities, boundaries, and implementation phase) are documented in `ARCHITECTURE.md` section 4 (expanded per-phase).

| # | Component | Primary Phase |
|---|---|---|
| 1 | Observability Layer | Phase 3 |
| 2 | Telemetry Ingestion | Phase 3 |
| 3 | Event Processing | Phase 4 |
| 4 | System State Model | Phase 4 |
| 5 | Anomaly Detection Engine | Phase 5 |
| 6 | Dependency Graph | Phase 6 |
| 7 | Root Cause Analysis Engine | Phase 6 |
| 8 | Incident Intelligence Engine | Phase 7 |
| 9 | AI Reasoning Layer | Phase 7 |
| 10 | Recovery Planner | Phase 8 |
| 11 | Policy Engine | Phase 9 |
| 12 | Risk Assessment | Phase 9 |
| 13 | Human Approval Layer | Phase 9 |
| 14 | Action Executor | Phase 10 |
| 15 | Verification Engine | Phase 11 |
| 16 | Feedback / Learning Layer | Phase 11 |
| 17 | Persistence Layer | Phase 1 |
| 18 | Dashboard / User Interface | Phase 12 |

---

## 5. Data Flow Summary

```
Infrastructure Telemetry
    → Observability Layer (normalize)
    → State Intelligence (model system state)
    → Anomaly Detection (identify deviations)
    → Incident record created
    → Dependency graph traversal
    → Root cause hypotheses generated
    → AI Reasoning (synthesize, explain)
    → Recovery Plan generated
    → Policy Engine (evaluate, authorize/escalate)
    → [Human Approval if required]
    → Action Executor (execute)
    → [Wait observation window]
    → Verification Engine (confirm recovery)
    → Outcome persisted
    → Feedback / Learning updated
    → Return to observation
```

---

## 6. Target Repository Structure

> **Target structure — future implementation.** Not all directories exist yet.

```
synapseops/
│
├── backend/                     # FastAPI backend application
│   ├── api/                     # API route handlers
│   ├── core/                    # Core configuration, dependencies
│   ├── intelligence/            # Intelligence engine components
│   │   ├── detection/           # Anomaly detection
│   │   ├── diagnosis/           # Root cause analysis
│   │   ├── reasoning/           # AI/LLM reasoning layer
│   │   ├── planning/            # Recovery planning
│   │   └── verification/        # Verification engine
│   ├── execution/               # Action executor
│   ├── policy/                  # Policy and safety engine
│   ├── state/                   # System state model
│   ├── telemetry/               # Telemetry ingestion and normalization
│   ├── models/                  # Pydantic data models
│   └── persistence/             # Database interaction layer
│
├── frontend/                    # Next.js operator dashboard
│   ├── src/
│   │   ├── app/                 # Next.js app router
│   │   ├── components/          # UI components
│   │   └── lib/                 # API clients, utilities
│   └── public/
│
├── simulator/                   # Simulated infrastructure environment
│   ├── services/                # Simulated microservices
│   ├── failures/                # Failure injection scripts
│   └── docker/                  # Docker configuration for simulator
│
├── intelligence/                # Standalone ML/AI experiment modules
│   ├── notebooks/               # Colab-compatible notebooks
│   ├── models/                  # Trained model artifacts
│   └── experiments/             # Experiment scripts
│
├── infrastructure/              # Real infrastructure configuration
│   ├── prometheus/              # Prometheus configuration
│   ├── grafana/                 # Grafana dashboards
│   └── kubernetes/              # Kubernetes manifests (future)
│
├── tests/                       # All project tests
│   ├── unit/
│   ├── integration/
│   └── end_to_end/
│
├── experiments/                 # Research experiments and benchmarks
│
├── scripts/                     # Developer and operational scripts
│
├── docs/                        # Project documentation
│
├── docker/                      # Docker and Docker Compose files
│
├── .github/                     # GitHub Actions, issue templates, PR templates
│
├── README.md
└── docker-compose.yml           # Future: full stack orchestration
```

---

## 7. Architecture Evolution Strategy

The architecture is designed to evolve incrementally. New components should be introduced only when there is a clear requirement and when the previous phase's foundations are stable.

Architectural changes that would affect more than one layer, introduce new external dependencies, or change fundamental data flow patterns require a formal Architecture Decision Record (see `ARCHITECTURE_DECISIONS.md`).

The architecture at any given phase should be the simplest architecture capable of supporting that phase's requirements while preserving the design patterns established by previous phases.
