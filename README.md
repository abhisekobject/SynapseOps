# SynapseOps

**Autonomous Infrastructure Intelligence & Self-Healing System**

> 🟢 **Current Status: Phase 16 — Adaptive Decision Intelligence (COMPLETE)**  
> The core system is fully implemented and validated across all 16 phases, proving the end-to-end loop from Observation through Adaptive Learning and Decision Support.

---

## Project Overview

SynapseOps is a long-term engineering and research project exploring how AI-assisted reasoning can be combined with deterministic safety controls to help infrastructure systems observe, understand, diagnose, and recover from failures.

The core operational loop:

```
OBSERVE → DETECT → UNDERSTAND → DIAGNOSE → REASON → PLAN → SAFETY/POLICY → ACT → VERIFY → LEARN
```

This is a personal engineering project built for serious learning, systems thinking, portfolio development, and research exploration. It is not a production system.

---

## Project Status: Complete

The conceptual development roadmap has reached **Phase 16 — Adaptive Decision Intelligence**. The repository contains a complete, integrated, and research-grade autonomous infrastructure intelligence loop.

### Core Capabilities Implemented

| Capability | Phase | Status |
|---|---|---|
| **Simulation & Infrastructure** | Phase 1-2 | ✅ Complete |
| **Observability & Telemetry** | Phase 3 | ✅ Complete |
| **State & Anomaly Detection** | Phase 4-5 | ✅ Complete |
| **Dependency Graph & RCA** | Phase 6 | ✅ Complete |
| **AI Incident Reasoning** | Phase 7 | ✅ Complete |
| **Recovery Planning** | Phase 8 | ✅ Complete |
| **Safety & Policy Engine** | Phase 9 | ✅ Complete |
| **Constrained Execution** | Phase 10 | ✅ Complete |
| **Verification & Evaluation** | Phase 11-12 | ✅ Complete |
| **Episodic Memory** | Phase 13 | ✅ Complete |
| **Operational Learning** | Phase 14 | ✅ Complete |
| **Operations Console (UI)** | Phase 15 | ✅ Complete |
| **Adaptive Decision Intelligence** | Phase 16 | ✅ Complete |

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
│   ├── ROADMAP.md              16-phase development trajectory
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
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 16-phase development plan |
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
| Phase 2 | Infrastructure simulation environment | ✅ Complete |
| Phase 3 | Observability pipeline | ✅ Complete |
| Phase 4–12 | State, RCA, Reasoning, Planning, Safety, Execution, Verification | ✅ Complete |
| Phase 13-16 | Memory, Learning, Ops Console, Decision Intelligence | ✅ Complete |

---

## License

MIT — Personal engineering and research project.
