# SynapseOps

**Autonomous Infrastructure Intelligence & Self-Healing System**

> 🟡 **Current Status: Phase 7 — AI Incident Reasoning**  
> Prometheus metrics, OpenTelemetry tracing, Event mapping, Anomaly Detection, Dependency Root Cause Analysis, and AI Incident Reasoning are implemented.  
> Planning, remediation, and autonomous recovery are not yet implemented.

---

## Project Overview

SynapseOps is a long-term engineering and research project exploring how AI-assisted reasoning can be combined with deterministic safety controls to help infrastructure systems observe, understand, diagnose, and recover from failures.

The core operational loop:

```
OBSERVE → DETECT → UNDERSTAND → DIAGNOSE → REASON → PLAN → SAFETY/POLICY → ACT → VERIFY → LEARN
```

This is a personal engineering project built for serious learning, systems thinking, portfolio development, and research exploration. It is not a production system.

---

## Current Phase: Phase 3 — Observability & Telemetry

### What exists now

| Capability | Status |
|---|---|
| FastAPI application with structured startup/shutdown | ✅ |
| Health endpoints (liveness, readiness, summary) | ✅ |
| Pydantic Settings — environment-based configuration | ✅ |
| Core domain models: Incident, Anomaly, Action, Outcome | ✅ |
| PostgreSQL integration (SQLAlchemy async) | ✅ |
| Database migration infrastructure (Alembic) | ✅ |
| Redis integration layer | ✅ |
| Structured application logging (structlog) | ✅ |
| Exception handling — no internal error leakage | ✅ |
| Unit test suite (pytest) — 207 tests | ✅ |
| Linting and formatting (Ruff) | ✅ |
| Docker Compose local development stack | ✅ |
| OpenAPI documentation (`/docs`, `/redoc`) | ✅ |
| Infrastructure simulator (gateway, API, worker) | ✅ Phase 2 |
| Failure injection API + named scenario library | ✅ Phase 2 |
| Prometheus metrics (`/metrics`, custom registry) | ✅ Phase 3 |
| OpenTelemetry tracing → Jaeger (OTLP gRPC) | ✅ Phase 3 |
| Request correlation (X-Request-ID + structlog context) | ✅ Phase 3 |
| Grafana dashboard (pre-provisioned) | ✅ Phase 3 |

### What is NOT implemented yet

| Capability | Planned Phase |
|---|---|
| System state engine | Phase 4 |
| Anomaly detection (statistical / ML) | Phase 5 |
| Dependency graph and root cause analysis | Phase 6 |
| LLM-assisted incident reasoning (Gemini/OpenAI) | Phase 7 |
| Recovery planner | Phase 8 |
| Policy engine and human approval | Phase 9 |
| Action executor | Phase 10 |
| Verification and learning engine | Phase 11 |
| Evaluation dashboard | Phase 12 |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SynapseOps Backend                   │
│                                                         │
│  FastAPI Application                                    │
│  ├── core/          Configuration, logging, errors      │
│  ├── api/           HTTP routes                         │
│  ├── models/        Domain (Pydantic) + DB (SQLAlchemy) │
│  ├── db/            Engine and session management       │
│  └── cache/         Redis client                        │
│                                                         │
│  External Services (Phase 1)                            │
│  ├── PostgreSQL     Primary database                    │
│  └── Redis          Cache / short-lived state           │
└─────────────────────────────────────────────────────────┘
```

The full target architecture is documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

The AI reasoning and action execution layers are architecturally separated. The LLM (Phase 7+) cannot directly execute actions — all proposed actions pass through schema validation, precondition checks, policy evaluation, and authorization before execution.

---

## Repository Structure

```
SynapseOps/
├── backend/                    Application source code
│   ├── main.py                 Application entry point
│   ├── core/                   Config, logging, errors
│   ├── api/                    Routes and API router
│   ├── models/
│   │   ├── domain/             Pydantic domain models
│   │   └── db/                 SQLAlchemy ORM models
│   ├── db/                     Database engine and sessions
│   └── cache/                  Redis client
├── alembic/                    Database migrations
│   └── versions/               Migration scripts
├── tests/
│   ├── unit/                   Unit tests (no external deps)
│   └── integration/            Integration tests (require DB/Redis)
├── docs/                       Project documentation (Phase 0+)
│   ├── PROJECT_VISION.md       Vision and problem definition
│   ├── ARCHITECTURE.md         System architecture
│   ├── ROADMAP.md              12-phase development trajectory
│   ├── SAFETY.md               Safety architecture
│   ├── AI_DESIGN.md            AI philosophy and boundaries
│   ├── TECH_STACK.md           Technology decisions
│   ├── ENGINEERING_PRINCIPLES.md  Core design principles
│   ├── DEVELOPMENT.md          Development workflow
│   ├── SETUP.md                Development setup guide
│   └── ...
├── .env.example                Environment variable template
├── pyproject.toml              Project metadata and tool config
├── alembic.ini                 Alembic configuration
├── Dockerfile                  Container image
└── docker-compose.yml          Local development stack
```

---

## Quick Start

### Prerequisites

- Python ≥ 3.11
- [uv](https://github.com/astral-sh/uv) (package manager)
- Docker Desktop (for PostgreSQL + Redis)

### Setup

```bash
# 1. Create virtual environment
uv venv .venv --python 3.11
source .venv/bin/activate

# 2. Install dependencies
uv pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD at minimum

# 4. Start PostgreSQL and Redis
docker-compose up -d postgres redis

# 5. Run database migrations
alembic upgrade head

# 6. Start the API
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now running at `http://localhost:8000`.

| URL | Description |
|---|---|
| `http://localhost:8000/health` | Health summary |
| `http://localhost:8000/health/live` | Liveness probe |
| `http://localhost:8000/health/ready` | Readiness probe |
| `http://localhost:8000/docs` | Interactive API docs |

See [`docs/SETUP.md`](docs/SETUP.md) for the full setup guide including troubleshooting.

---

## Running Tests

```bash
# Unit tests only (no DB/Redis required)
pytest tests/unit/ -v

# All tests with coverage report
pytest --cov=backend --cov-report=term-missing
```

---

## Linting

```bash
ruff check .           # Check for lint errors
ruff format . --check  # Check formatting
ruff format .          # Apply formatting
```

---

## Docker Compose (Full Local Stack)

> Requires Docker Desktop.

```bash
docker-compose up -d --build
docker-compose logs -f api
```

---

## Documentation

| Document | Description |
|---|---|
| [`docs/SETUP.md`](docs/SETUP.md) | Development setup guide |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 12-phase development plan |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture |
| [`docs/SAFETY.md`](docs/SAFETY.md) | Safety model and action boundaries |
| [`docs/AI_DESIGN.md`](docs/AI_DESIGN.md) | AI philosophy and design |
| [`docs/ENGINEERING_PRINCIPLES.md`](docs/ENGINEERING_PRINCIPLES.md) | Core design principles |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Technology decisions |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | Research questions |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Evaluation metrics |
| [`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md) | ADR log |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Project terminology |

---

## Phase History

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Project definition and engineering constitution | ✅ Complete |
| Phase 1 | Project foundation (FastAPI, DB, Redis, tests) | ✅ Complete |
| Phase 2 | Infrastructure simulation environment | 🔲 Planned |
| Phase 3 | Observability pipeline | 🔲 Planned |
| Phase 4–12 | See [`docs/ROADMAP.md`](docs/ROADMAP.md) | 🔲 Planned |

---

## License

MIT — Personal engineering and research project.
