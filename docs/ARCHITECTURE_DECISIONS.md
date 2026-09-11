# Architecture Decisions — SynapseOps

> This document serves two purposes:
> 1. The authoritative record of significant architectural decisions made throughout the project
> 2. The guiding framework for avoiding overengineering
>
> All significant architectural decisions must be recorded here using the ADR (Architecture Decision Record) format.

---

## Part 1: Overengineering Avoidance Framework

### The Core Rule

> **Prefer the simplest architecture capable of supporting the current phase's requirements while preserving the design patterns established by previous phases.**

This is not an invitation to write poor code. Simple architecture and high code quality are compatible. "Simple" means:

- No components that don't yet serve a requirement
- No dependencies that don't yet deliver value
- No abstractions that aren't required by more than one concrete use
- No distributed systems complexity before it is needed
- No AI/ML where deterministic approaches are adequate

### Technology Introduction Criteria

Every technology introduction beyond the initial stack must satisfy all three criteria:

1. **There is a specific, documented requirement it addresses** — not a hypothetical future requirement
2. **A simpler approach was considered and found insufficient** — and the insufficiency is documented
3. **The maintenance and complexity cost is worth the value** — evaluated honestly

### Specific Deferral Decisions

The following technologies are explicitly deferred unless a documented requirement and ADR justify their introduction:

| Technology | Deferral Rationale |
|---|---|
| **Apache Kafka** | Event throughput and architectural decoupling don't warrant it initially. Redis queuing and PostgreSQL are sufficient. Introduce only if event volume or replay requirements demand it. |
| **Kubernetes** | Container orchestration is not needed in the development and simulation phases. Docker Compose is sufficient. Introduce only if deployment complexity or scaling genuinely requires it. |
| **Neo4j / graph database** | NetworkX in-memory graphs plus PostgreSQL persistence are sufficient for the initial dependency graph. Introduce only if graph query complexity, scale, or traversal performance requirements exceed what this approach provides. |
| **Separate microservices** | The backend starts as a single FastAPI application. Decompose into services only when there are clear, specific reasons — different scaling requirements, team boundaries, or deployment independence needs — not because microservices sound better. |
| **PyTorch / deep learning** | scikit-learn covers the initial ML requirements. Introduce PyTorch only if anomaly detection or other ML requirements demonstrably exceed what scikit-learn can provide. |
| **LangChain / LlamaIndex** | Direct LLM API calls with carefully engineered prompts are preferred initially. Introduce AI orchestration frameworks only if complexity justifies the abstraction layer. |
| **Celery / distributed task queue** | Background tasks start with asyncio or simple threading. Introduce Celery only if task management complexity, retry handling, or distribution requirements demand it. |
| **Elasticsearch** | Log search starts with structured PostgreSQL queries or Loki. Introduce Elasticsearch only if search requirements exceed what these provide. |

### Complexity Anti-Patterns to Avoid

| Anti-Pattern | Why to Avoid |
|---|---|
| **Speculative generality** | Building for requirements that don't yet exist ("we might need this later") |
| **Technology cargo-culting** | Adopting technologies because they are used by large companies whose requirements are different from ours |
| **Abstraction pyramids** | Multiple layers of abstraction where one would suffice |
| **Premature distribution** | Splitting into distributed components before understanding where the boundaries should be |
| **Framework maximalism** | Using a full framework for a problem that needs a library |
| **Dependency accumulation** | Adding packages for small conveniences without considering maintenance cost |

---

## Part 2: Architecture Decision Records

ADRs are written when a significant architectural decision is made. "Significant" means:

- The decision affects more than one component
- The decision introduces a new external dependency
- The decision changes fundamental data flow patterns
- The decision would be difficult or expensive to reverse
- Reasonable alternatives exist and were considered

### ADR Format

```
## ADR-NNN: [Decision Title]

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Superseded | Deprecated
**Supersedes**: ADR-NNN (if applicable)
**Context**: What problem prompted this decision?
**Decision**: What was decided?
**Alternatives Considered**: What else was evaluated?
**Rationale**: Why was this option selected?
**Consequences**: What are the known tradeoffs or future implications?
**Phase**: In which phase was this decision made?
```

---

## ADR-001: Python as the Primary Language

**Date**: 2026-09-11
**Status**: Accepted
**Context**: SynapseOps requires strong ML/AI ecosystem support, async I/O for telemetry processing, and rapid iteration for experimental components.
**Decision**: Python 3.11+ is the primary language for all backend, intelligence, and data processing components.
**Alternatives Considered**: Go (better concurrency, lower overhead, weaker ML ecosystem), Rust (best performance, steepest learning curve, minimal ML ecosystem), Node.js (strong async, poor ML ecosystem).
**Rationale**: Python's ML/data science ecosystem is unmatched. The performance requirements of early phases do not justify Go's or Rust's tradeoffs. Python's async support (asyncio, FastAPI) is adequate for the expected I/O patterns.
**Consequences**: CPU-bound performance will be lower than Go or Rust. Accepted: intelligence components are not expected to be compute-critical in early phases. If performance becomes a constraint, specific hot paths can be optimized with native extensions.
**Phase**: 0

---

## ADR-002: FastAPI as the Backend Framework

**Date**: 2026-09-11
**Status**: Accepted
**Context**: The SynapseOps backend requires an async API framework with strong type validation, automatic documentation, and Python ecosystem compatibility.
**Decision**: FastAPI is selected as the backend API framework.
**Alternatives Considered**: Django REST Framework (heavier, synchronous-first, more opinionated), Flask (lightweight but requires more manual wiring), Litestar (compelling alternative but smaller community).
**Rationale**: FastAPI is async-native, integrates directly with Pydantic v2, generates OpenAPI documentation automatically, and is well-suited to building structured API services with strong typing.
**Consequences**: FastAPI's async model requires attention to avoid blocking the event loop in CPU-bound operations. Offload heavy computation to thread pools or background tasks as needed.
**Phase**: 0

---

## ADR-003: PostgreSQL as the Primary Database

**Date**: 2026-09-11
**Status**: Accepted
**Context**: SynapseOps needs to persist incident records, telemetry summaries, system state, hypotheses, actions, outcomes, and feedback. The schema must be evolvable across phases.
**Decision**: PostgreSQL is the primary relational database.
**Alternatives Considered**: MongoDB (schema flexibility, but we benefit from relational integrity and SQL query power), SQLite (too limited for multi-process production use), MySQL (less feature-rich JSON support).
**Rationale**: PostgreSQL provides relational integrity for structured incident records, JSONB for flexible schema fields (telemetry, evidence, hypothesis detail), strong Python support via SQLAlchemy/asyncpg, and proven reliability.
**Consequences**: Requires a running PostgreSQL instance for development. Addressed by Docker Compose. Time-series metric storage may eventually require a dedicated time-series database if query performance on large metric datasets is inadequate.
**Phase**: 0

---

## ADR-004: NetworkX for Dependency Graph (Initial)

**Date**: 2026-09-11
**Status**: Accepted
**Context**: The dependency graph is central to root cause analysis. An implementation approach is needed.
**Decision**: NetworkX (Python graph library) is used for in-memory dependency graph construction and traversal. Graph topology is persisted in PostgreSQL.
**Alternatives Considered**: Neo4j (powerful but adds significant operational complexity early), Amazon Neptune (cloud-only, adds vendor dependency), tigergraph (enterprise-focused).
**Rationale**: NetworkX provides sufficient graph algorithms (shortest path, connected components, topological sort) for initial root cause analysis requirements. The graph is small enough (tens to hundreds of nodes in the simulator) for in-memory operation. Persistence in PostgreSQL (adjacency list representation) is straightforward.
**Consequences**: If future requirements include complex graph queries that NetworkX cannot efficiently support at scale, this decision will be revisited in an ADR. The boundary for that decision: NetworkX becomes inadequate when graph size or query complexity makes in-memory traversal impractical.
**Phase**: 0

---

## ADR-005: LLM Integration Deferred to Phase 7

**Date**: 2026-09-11
**Status**: Accepted
**Context**: LLM integration is a central future capability. When should it be introduced?
**Decision**: LLM API integration is deferred to Phase 7. Phases 1–6 use deterministic and statistical intelligence only.
**Rationale**: LLM reasoning is most valuable for synthesizing complex, heterogeneous evidence — a capability only meaningful once the foundational layers (telemetry, detection, dependency analysis) exist and produce real evidence. Introducing LLM integration before Phase 6 would mean prompting an LLM with insufficient grounded evidence, producing unreliable outputs. Building the deterministic foundation first allows LLM reasoning to augment genuine analytical capability rather than substitute for it.
**Consequences**: The system will have measurable analytical capability (detection, root cause) before LLM reasoning is added. This enables a clean A/B comparison of system quality with and without LLM augmentation — a valuable evaluation.
**Phase**: 0

---

*New ADRs will be added here as significant architectural decisions are made during implementation phases.*
