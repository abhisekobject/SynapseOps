# Technology Stack — SynapseOps

> This document defines the technology direction for SynapseOps. Technologies are categorized by their intended introduction phase. Nothing in this document implies that all listed technologies are installed or configured now.

---

## Categorization Key

| Category | Meaning |
|---|---|
| **INITIAL** | Introduced in early phases (1–4). Core to the system from the start. |
| **LATER** | Introduced in later phases when specific requirements materialize. |
| **CONDITIONAL** | Introduced only if requirements exceed what simpler options can provide. Requires an Architecture Decision Record. |

---

## Core Language

| Technology | Category | Rationale |
|---|---|---|
| **Python 3.11+** | INITIAL | Dominant language in ML/AI ecosystems, extensive libraries for data analysis, strong async support (asyncio), clear and readable syntax suitable for a long-term project. |

Python is the primary language for all backend, intelligence, and data-processing components.

---

## Backend Framework

| Technology | Category | Rationale |
|---|---|---|
| **FastAPI** | INITIAL | Modern, async-native Python web framework. Built-in Pydantic validation, automatic OpenAPI documentation, high performance for I/O-bound workloads. Well-suited for building the SynapseOps API layer and intelligence service endpoints. |

---

## Frontend

| Technology | Category | Rationale |
|---|---|---|
| **Next.js** | INITIAL | Production-grade React framework with file-based routing, server-side rendering, and strong TypeScript support. Suitable for the operator dashboard. |
| **TypeScript** | INITIAL | Adds type safety to the frontend, reducing runtime errors and improving maintainability. |
| **Tailwind CSS** | INITIAL | Utility-first CSS framework with excellent developer experience. Standard in modern Next.js projects. |

---

## Database

| Technology | Category | Rationale |
|---|---|---|
| **PostgreSQL** | INITIAL | Mature, reliable relational database. Will store incident records, hypotheses, actions, outcomes, feedback, and configuration. Well-supported by Python ORM tooling (SQLAlchemy). Capable of storing structured JSON for flexible schema needs. |
| **SQLAlchemy** | INITIAL | Python ORM for PostgreSQL interaction. Supports both synchronous and async operation. |
| **Alembic** | INITIAL | Database migration tool for SQLAlchemy. Required for managing schema evolution. |

---

## Cache / Short-Lived State / Queuing

| Technology | Category | Rationale |
|---|---|---|
| **Redis** | INITIAL | Used for caching frequently accessed system state, short-lived event queues, and real-time signal buffering. Not used as a primary database. |

---

## Containerization

| Technology | Category | Rationale |
|---|---|---|
| **Docker** | INITIAL | Container runtime for local development and the simulated infrastructure environment. All services will run as Docker containers. |
| **Docker Compose** | INITIAL | Container orchestration for local development and the simulator stack. Appropriate for Phase 0–9 development. |

---

## Container Orchestration (Production-Scale)

| Technology | Category | Rationale |
|---|---|---|
| **Kubernetes** | LATER | Introduced when container orchestration provides real value beyond what Docker Compose offers. Not required for early phases. Premature adoption would add significant operational complexity. |
| **Helm** | LATER | Kubernetes package manager. Only relevant if/when Kubernetes is adopted. |

---

## Observability Infrastructure

| Technology | Category | Rationale |
|---|---|---|
| **Prometheus** | INITIAL | Standard time-series metrics system. Will collect metrics from the simulated infrastructure and from SynapseOps components themselves. |
| **Grafana** | INITIAL | Visualization layer for Prometheus metrics. Used for human operator dashboards and for verifying SynapseOps telemetry collection. |
| **OpenTelemetry** | INITIAL | Vendor-neutral instrumentation SDK for generating traces and metrics from simulated services. |
| **Loki** | CONDITIONAL | Log aggregation system. Will be adopted if log analysis requirements exceed what structured log ingestion in PostgreSQL can reasonably provide. |

---

## Data Analysis & Machine Learning

| Technology | Category | Rationale |
|---|---|---|
| **NumPy** | LATER | Numerical computing foundation. Required by scikit-learn and most ML tooling. |
| **Pandas** | LATER | DataFrame-based data analysis. Useful for telemetry preprocessing, feature engineering, and model evaluation. |
| **scikit-learn** | LATER | Standard ML library. Will be used for anomaly detection (isolation forests, statistical models), classification, and evaluation. The first ML library adopted. |
| **PyTorch** | CONDITIONAL | Deep learning framework. Adopted only if requirements exceed what scikit-learn can provide — for example, time-series anomaly detection using LSTM or transformer models. Requires explicit justification. |

---

## Graph Analysis

| Technology | Category | Rationale |
|---|---|---|
| **NetworkX** | LATER | Python library for graph construction and analysis. Will be used for service dependency graph modeling and root cause propagation analysis. Appropriate for the initial graph requirements. |
| **Neo4j / graph database** | CONDITIONAL | Dedicated graph database. Adopted only if graph query complexity, scale, or persistence requirements exceed what NetworkX + PostgreSQL can reasonably support. Requires an Architecture Decision Record. |

---

## AI / LLM Reasoning

| Technology | Category | Rationale |
|---|---|---|
| **LLM API integration** | LATER | Integration with an LLM API (e.g., Google Gemini, OpenAI GPT) for incident reasoning, hypothesis synthesis, and explanation generation. Introduced in Phase 7. Not adopted before the foundational intelligence layers (detection, diagnosis) are operational. |
| **LangChain / LlamaIndex** | CONDITIONAL | AI orchestration frameworks. Adopted only if they provide clear value over direct API integration. Heavy frameworks introduce complexity and dependency risk that must be justified. |

---

## Testing

| Technology | Category | Rationale |
|---|---|---|
| **pytest** | INITIAL | Python testing framework. All unit, integration, and end-to-end tests will use pytest. |
| **pytest-asyncio** | INITIAL | Async test support for FastAPI components. |
| **httpx** | INITIAL | Async HTTP client used for testing FastAPI endpoints. |
| **factory_boy** | LATER | Test fixture factory library. Introduced when test data setup becomes complex. |

---

## Configuration & Environment Management

| Technology | Category | Rationale |
|---|---|---|
| **python-dotenv** | INITIAL | Environment variable loading from `.env` files for local development. |
| **Pydantic Settings** | INITIAL | Type-safe configuration management using Pydantic. Integrates with FastAPI's dependency injection. |

---

## Version Control & Collaboration

| Technology | Category | Rationale |
|---|---|---|
| **Git** | INITIAL | Version control. |
| **GitHub** | INITIAL | Remote repository, issue tracking, CI/CD (GitHub Actions). |

---

## CI/CD

| Technology | Category | Rationale |
|---|---|---|
| **GitHub Actions** | LATER | Automated testing, linting, and build validation. Introduced when the codebase is substantive enough to benefit. |

---

## Experimentation

| Technology | Category | Rationale |
|---|---|---|
| **Jupyter / Google Colab** | INITIAL | Notebook environment for ML experiments, data analysis, and model evaluation. Experiments are developed here before being integrated into the production codebase. |

---

## Code Quality

| Technology | Category | Rationale |
|---|---|---|
| **Ruff** | INITIAL | Fast Python linter and formatter. Replaces flake8 + isort + black with a single tool. |
| **mypy** | LATER | Static type checker for Python. Introduced when the codebase benefits from stricter type enforcement. |
| **pre-commit** | LATER | Git hook framework for automated code quality checks before commit. |

---

## What Is Explicitly NOT Adopted Without Justification

The following technologies are explicitly deferred unless a specific, documented requirement justifies their adoption:

| Technology | Reason for Deferral |
|---|---|
| Apache Kafka | Premature for early phases. Event throughput does not warrant it initially. |
| Celery | Background task processing will be handled more simply initially. |
| Elasticsearch | Log search can be handled by Loki or structured PostgreSQL initially. |
| RabbitMQ | Redis queuing is sufficient for initial requirements. |
| Multiple microservices | Premature decomposition before architecture stabilizes. |
| Terraform | Infrastructure-as-code not required until production infrastructure exists. |
| Pulumi | Same as Terraform. |
| Ray / Dask | Distributed computing not required initially. |

Each of these may eventually become appropriate. Their adoption requires an Architecture Decision Record explaining the specific requirement and why simpler alternatives are insufficient.

---

## Technology Adoption Summary

```
PHASE 1–2   Python, FastAPI skeleton, Docker, Docker Compose, pytest
PHASE 3     Prometheus, Grafana, OpenTelemetry
PHASE 4     PostgreSQL, Redis, SQLAlchemy, Alembic
PHASE 5     NumPy, Pandas, scikit-learn (anomaly detection)
PHASE 6     NetworkX (dependency graph)
PHASE 7     LLM API integration, Next.js frontend begin
PHASE 8+    Additional components as justified
```
