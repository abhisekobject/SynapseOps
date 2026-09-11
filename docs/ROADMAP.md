# Development Roadmap — SynapseOps

> **Status**: This is a living roadmap. Phase objectives and scope may be refined as earlier phases inform later ones. Each phase will be fully specified in a dedicated implementation prompt before work begins.

---

## How to Read This Roadmap

Each phase has:
- **Objective**: What it aims to accomplish
- **Why it exists**: The architectural necessity
- **Major components**: What will be built
- **Expected outcomes**: What a completed phase looks like
- **Prerequisites**: What must exist before this phase begins
- **Boundaries**: What should NOT be implemented before this phase

Phases should be executed sequentially. Starting a phase before its prerequisites are complete risks building on unstable foundations.

---

## Phase 0 — Project Definition & Engineering Constitution

**Status**: ✅ Active

### Objective
Establish the complete conceptual foundation, architecture, engineering principles, safety philosophy, technology direction, and documentation structure for SynapseOps before any implementation begins.

### Why it exists
Building complex systems without a clear foundation leads to architectural drift, inconsistent design decisions, and rework. Phase 0 ensures all future implementation has a coherent reference point.

### Major components
- Project vision and problem definition
- High-level system architecture
- Engineering principles
- AI design philosophy
- Safety model
- Technology direction
- Development philosophy
- Glossary and terminology
- Research direction
- Evaluation framework
- GitHub quality standards
- Architecture decision framework
- Phase roadmap

### Expected outcomes
A fully documented project foundation. No application code exists. Another developer could read the documentation and understand what SynapseOps is, why it exists, how it is designed, and what it will become.

### Prerequisites
None.

### What must NOT be implemented yet
Everything in Phases 1–12. No application code, no infrastructure configuration, no ML models, no database schemas.

---

## Phase 1 — Repository + Core Architecture

**Status**: 📋 Planned

### Objective
Establish the repository structure, development environment, core application skeletons, configuration system, and persistence foundation that all subsequent phases will build on.

### Why it exists
Future phases need a stable, operable foundation with a working environment, a testable application skeleton, and a functioning database before building intelligence components on top.

### Major components
- Git repository initialization with `.gitignore`, `README`, branch structure
- Python project structure with Ruff, pytest, pyproject.toml
- FastAPI application skeleton with health endpoint
- Pydantic Settings configuration system
- PostgreSQL schema foundation (core tables: incidents, events, anomalies, actions, outcomes)
- Alembic migration setup
- Redis integration skeleton
- Docker Compose for local development (API + DB + Redis)
- Basic CI skeleton (GitHub Actions)
- Core Pydantic data models for all primary entities

### Expected outcomes
A running local development environment. `docker-compose up` starts the API, database, and cache. `pytest` runs with zero failures. Core data models exist. Database schema has been applied.

### Prerequisites
Phase 0 complete.

### What must NOT be implemented yet
Telemetry ingestion, anomaly detection, ML models, dependency graph, LLM integration, simulator, frontend.

---

## Phase 2 — Infrastructure Simulation Environment

**Status**: 📋 Planned

### Objective
Build a controllable simulated distributed infrastructure that SynapseOps can observe and operate against.

### Why it exists
SynapseOps cannot be developed and tested against real production infrastructure. A simulated environment allows controlled failure injection, reproducible testing, and safe experimentation.

### Major components
- Simulated distributed system: Gateway → API Service → Worker → PostgreSQL (+ Redis)
- Each simulated service emits realistic metrics, logs, and traces via OpenTelemetry
- Failure injection API: trigger controlled failures (crash, latency, CPU pressure, DB connection exhaustion, error rate spike, etc.)
- Docker Compose configuration for the full simulator stack
- Baseline scenario: all services healthy with realistic traffic
- Documented failure scenarios (initial set of at least 5 scenarios)

### Simulated failure scenarios (initial set)
1. Worker service crash
2. API service elevated error rate
3. Database connection pool exhaustion
4. CPU pressure on worker
5. Cascade failure (DB slow → worker queue backup → API latency)

### Expected outcomes
Running `docker-compose up` starts both SynapseOps components and the simulated infrastructure. Failures can be injected via API call or script. Simulated services emit real-looking telemetry. The scenario is reproducible.

### Prerequisites
Phase 1 complete.

### What must NOT be implemented yet
Anomaly detection, ML models, dependency graph, LLM integration, frontend, autonomous action execution.

---

## Phase 3 — Observability & Telemetry

**Status**: 📋 Planned

### Objective
Collect, normalize, and store telemetry from the simulated infrastructure within SynapseOps.

### Why it exists
SynapseOps cannot reason about infrastructure it cannot observe. Telemetry ingestion is the foundational data pipeline for all intelligence components.

### Major components
- Prometheus metric collection from simulated services
- Structured log ingestion from simulated services
- Distributed trace ingestion via OpenTelemetry
- Discrete event ingestion (deployment, restart, health-check events)
- Telemetry normalization layer
- Telemetry storage (metrics in time-series format, logs and events in PostgreSQL)
- Grafana dashboards for human-visible telemetry validation
- Telemetry API endpoints for querying current and historical signals

### Expected outcomes
SynapseOps collects all four telemetry types from the simulator. Metrics are queryable via API. A Grafana dashboard shows live telemetry. Injecting a failure is visible in the telemetry. All data is persisted.

### Prerequisites
Phases 1 and 2 complete.

### What must NOT be implemented yet
Anomaly detection, dependency graph, AI reasoning, frontend, action execution.

---

## Phase 4 — System State & Event Intelligence

**Status**: 📋 Planned

### Objective
Build a dynamic model of current system state from ingested telemetry. Detect state transitions. Begin event correlation.

### Why it exists
Raw telemetry is not the same as system understanding. The system state model is the structured representation of "what is currently happening" — the input to all higher-level intelligence.

### Major components
- System state model: per-service health status, current metric summaries, recent events
- State transition detection: healthy → degraded → failing → recovering
- Event correlation: group related signals within a time window
- Incident record creation from correlated events
- System state API: queryable current and historical state
- State change notifications (internal events for downstream components)

### Expected outcomes
When a failure is injected, SynapseOps creates an incident record, updates service health status, and correlates related signals. The system state is queryable via API. State transitions are logged.

### Prerequisites
Phase 3 complete.

### What must NOT be implemented yet
ML-based anomaly detection, dependency graph, AI reasoning, action execution, frontend.

---

## Phase 5 — Anomaly Detection

**Status**: 📋 Planned

### Objective
Detect anomalous signals in telemetry using statistical and ML-based approaches that go beyond simple static thresholds.

### Why it exists
Threshold-based alerting is brittle — it generates excessive false positives on dynamic workloads and misses gradual degradation. Statistical and ML-based anomaly detection can identify deviations from learned normal behavior more reliably.

### Major components
- Statistical anomaly detection: rolling baseline (mean, std), z-score analysis
- ML-based anomaly detection: Isolation Forest for multivariate metric analysis
- Anomaly scoring: severity score and confidence per detected anomaly
- Anomaly persistence and querying
- Evaluation framework: precision, recall, false-positive rate on labeled simulator scenarios
- Baseline experiment in Jupyter notebook (Google Colab compatible)

### Expected outcomes
SynapseOps detects anomalies from injected failures with measured precision and recall against labeled scenarios. Anomaly detection outperforms or complements simple threshold detection. Detection results feed the incident record.

### Prerequisites
Phase 4 complete.

### What must NOT be implemented yet
Dependency graph, root cause analysis, AI reasoning, action execution, frontend.

---

## Phase 6 — Root Cause & Dependency Intelligence

**Status**: 📋 Planned

### Objective
Build a service dependency graph and use it to trace failure propagation and generate root cause hypotheses.

### Why it exists
Anomaly detection identifies that something is wrong. Root cause analysis attempts to identify why it's wrong and where it originated. Service dependencies are essential for distinguishing root causes from downstream symptoms.

### Major components
- Dependency graph construction (from configuration + discovered topology)
- Dependency graph storage and querying (NetworkX + PostgreSQL)
- Root cause propagation analysis: trace anomalies through the dependency graph
- Hypothesis generation: ranked list of probable root causes with evidence
- Confidence scoring for each hypothesis
- Root cause analysis API

### Expected outcomes
For each injected failure scenario, SynapseOps generates a root cause hypothesis that correctly identifies the origin service in majority of cases (success criteria defined at phase start). Hypotheses include the evidence and the propagation path.

### Prerequisites
Phase 5 complete.

### What must NOT be implemented yet
LLM integration, recovery planning, action execution, frontend.

---

## Phase 7 — AI Incident Reasoning

**Status**: 📋 Planned

### Objective
Integrate an LLM reasoning layer that synthesizes telemetry, dependency analysis, and historical context into structured incident understanding and human-readable explanations.

### Why it exists
Root cause analysis produces hypotheses. AI reasoning synthesizes the full evidence context into a coherent incident narrative — explaining what happened, why, and what the evidence shows — in a way that structured ML cannot.

### Major components
- LLM API integration with structured output (Pydantic schemas)
- Evidence grounding system (telemetry context injection into prompts)
- Structured prompt templates (versioned, tested)
- Incident interpretation output: hypothesis synthesis, confidence, explanation
- Historical incident context retrieval (RAG over past incidents)
- Evaluation: accuracy of AI interpretations vs. ground truth on labeled scenarios
- Fallback behavior when LLM is unavailable

### Expected outcomes
For injected failures, SynapseOps produces an AI-synthesized incident interpretation with evidence, hypothesis, and explanation. The output conforms to a defined schema. Fallback behavior exists. Frontend begins development (Phase 7 or 12).

### Prerequisites
Phase 6 complete.

### What must NOT be implemented yet
Autonomous action execution, policy engine implementation, full frontend.

---

## Phase 8 — Recovery Planning

**Status**: 📋 Planned

### Objective
Generate structured candidate recovery plans for detected and diagnosed incidents.

### Why it exists
Understanding the incident is necessary but not sufficient. The system must propose what to do about it. Recovery planning translates incident understanding into candidate actions with risk assessments.

### Major components
- Recovery action catalog: defined action types, preconditions, expected effects, risk attributes
- Recovery plan generator: maps incident type to candidate actions
- Action ranking: by expected effectiveness and risk
- Risk estimation: assign risk level to each candidate action
- Recovery plan API: human-queryable and machine-consumable
- Plan evaluation framework

### Expected outcomes
For each diagnosed incident, SynapseOps generates a ranked recovery plan with candidate actions, risk assessments, and rationale. Plans are queryable and human-readable.

### Prerequisites
Phase 7 complete.

### What must NOT be implemented yet
Autonomous action execution, policy enforcement, human approval UI.

---

## Phase 9 — Safety / Policy / Human Approval

**Status**: 📋 Planned

### Objective
Implement the policy engine, risk classification system, and human approval layer that govern what actions the system is authorized to execute.

### Why it exists
Recovery plans are proposals. They become actions only after passing through a safety boundary. This phase implements that boundary.

### Major components
- Risk scoring function (deterministic)
- Policy rule engine (initial rule set)
- Action authorization decision: autonomous vs. human approval vs. denied
- Human approval queue (API + UI)
- Human approval decision capture
- Audit logging (all policy and authorization decisions)
- Rate limiting
- Dry-run mode
- Simulation mode

### Expected outcomes
SynapseOps correctly routes low-risk actions to autonomous authorization and high-risk actions to human approval. Policy decisions are logged. Human operators can approve, deny, or modify proposed actions. No autonomous execution yet.

### Prerequisites
Phase 8 complete.

### What must NOT be implemented yet
Actual infrastructure execution (deferred to Phase 10).

---

## Phase 10 — Controlled Autonomous Execution

**Status**: 📋 Planned

### Objective
Implement the bounded action executor that carries out authorized recovery actions against the simulated infrastructure.

### Why it exists
The operational loop requires execution. This phase closes the loop from detection through to action — but only after the safety layer (Phase 9) is fully operational.

### Major components
- Action executor (bounded, schema-driven)
- Integration with simulated infrastructure control APIs
- Action result capture (success, failure, timeout)
- Post-execution state recording
- Full operational loop integration (observe → detect → diagnose → plan → authorize → execute)

### Expected outcomes
SynapseOps can autonomously execute authorized low-risk recovery actions against the simulator. The execution is logged, bounded, and validated. High-risk actions still require human approval.

### Prerequisites
Phase 9 complete.

### What must NOT be implemented yet
Verification engine (Phase 11), learning loop (Phase 11).

---

## Phase 11 — Verification + Feedback + Learning

**Status**: 📋 Planned

### Objective
Implement closed-loop verification (did the system actually recover?) and the feedback/learning mechanisms that improve future decisions.

### Why it exists
Execution success is not recovery success. This phase completes the loop and adds the adaptive intelligence that distinguishes a learning system from a static one.

### Major components
- Verification engine: post-action telemetry observation and recovery confirmation
- Rollback trigger: when verification fails
- Outcome persistence: full incident-to-outcome records
- Operator feedback capture
- Historical outcome analysis
- Initial learning mechanisms: action effectiveness weighting, hypothesis confidence updates

### Expected outcomes
SynapseOps completes the full closed-loop: observe → detect → diagnose → plan → authorize → execute → verify → record. System behavior improves measurably with accumulated incident history.

### Prerequisites
Phase 10 complete.

---

## Phase 12 — Dashboard + Evaluation + Documentation

**Status**: 📋 Planned

### Objective
Build the operator dashboard, run comprehensive evaluation, produce demonstration-quality documentation and demos.

### Why it exists
The system's operational value must be visible and evaluable. This phase makes the system presentable, measurable, and demonstrable.

### Major components
- Next.js operator dashboard (if not yet built)
- Dashboard: incident view, evidence, hypothesis, recovery plan, human approval UI
- Dashboard: historical incident records, outcomes
- Comprehensive evaluation: all detection, diagnosis, recovery, and safety metrics measured
- Demo scenario scripts
- Updated documentation: setup guide, demo guide, architecture diagrams
- GitHub portfolio quality: README, screenshots, diagrams

### Expected outcomes
SynapseOps can be demonstrated end-to-end from failure injection to verified recovery. The dashboard provides full visibility. Evaluation metrics are published. The repository meets GitHub portfolio quality standards.

### Prerequisites
Phase 11 complete.

---

## Roadmap Summary

| Phase | Title | Key Deliverable |
|---|---|---|
| **0** | Project Definition | Engineering constitution, architecture, principles |
| **1** | Core Architecture | Running application skeleton with DB and tests |
| **2** | Infrastructure Simulation | Controllable simulated system with failure injection |
| **3** | Observability & Telemetry | All four telemetry types collected and stored |
| **4** | System State & Events | Incident creation, state model, event correlation |
| **5** | Anomaly Detection | Statistical + ML anomaly detection with evaluation |
| **6** | Root Cause Intelligence | Dependency graph + root cause hypotheses |
| **7** | AI Incident Reasoning | LLM-synthesized incident understanding |
| **8** | Recovery Planning | Structured recovery plans with risk assessment |
| **9** | Safety / Policy | Policy engine, authorization, human approval |
| **10** | Autonomous Execution | Bounded action execution against simulator |
| **11** | Verification + Learning | Closed-loop recovery with outcome recording |
| **12** | Dashboard + Evaluation | Full demo capability and evaluation metrics |
