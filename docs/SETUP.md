# SynapseOps Development Setup Guide

> **Phase 1 — Project Foundation**
> This guide covers local development setup for the Phase 1 foundation.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | ≥ 3.11 | 3.14 confirmed working |
| uv | ≥ 0.12 | Preferred package manager |
| Docker Desktop | ≥ 4.x | Required for PostgreSQL + Redis |
| Git | any | Already initialized |

Check your versions:

```bash
python3 --version
uv --version
docker --version
```

---

## 1. Clone / Open the Repository

If you have already cloned the repository, skip this step.

```bash
git clone <your-remote-url> SynapseOps
cd SynapseOps
```

---

## 2. Create the Virtual Environment

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
uv pip install -e ".[dev]"
```

This installs:
- All production dependencies (FastAPI, SQLAlchemy, Redis, etc.)
- All development dependencies (pytest, ruff, httpx, etc.)
- The `synapseops` package in editable mode

---

## 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your local values. At minimum, set:

```dotenv
POSTGRES_PASSWORD=your_local_password
```

**Never commit `.env` to version control.** It is listed in `.gitignore`.

---

## 5. Start PostgreSQL and Redis

### Using Docker Compose (recommended)

```bash
# Start only the database services (not the API container)
docker-compose up -d postgres redis
```

Wait for both services to be healthy:

```bash
docker-compose ps
```

Both should show `healthy` status.

### Alternative: Existing local PostgreSQL/Redis

If you have PostgreSQL and Redis running locally, update your `.env` with the
correct host, port, credentials, and database name.

---

## 6. Run Database Migrations

With PostgreSQL running and `.env` configured:

```bash
# Activate venv if not already active
source .venv/bin/activate

# Apply the initial schema migration
alembic upgrade head
```

Expected output:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema — Phase 1 foundation tables.
```

Verify the schema was created:

```bash
# Connect to PostgreSQL and check tables
docker exec -it synapseops-postgres psql -U synapseops -d synapseops -c "\dt"
```

Expected tables: `incidents`, `anomalies`, `actions`, `outcomes`

### Migration commands reference

```bash
alembic upgrade head       # Apply all pending migrations
alembic downgrade -1       # Roll back one migration
alembic current            # Show current migration revision
alembic history            # List all migrations
```

---

## 7. Start the FastAPI Application

```bash
# From the project root with venv active
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables hot-reloading during development.

Verify the application is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "app": "SynapseOps",
  "environment": "development",
  "version": "0.1.0",
  "phase": "Phase 1 — Project Foundation"
}
```

### Available endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Combined health summary |
| `GET /health/live` | Liveness probe (process only) |
| `GET /health/ready` | Readiness probe (DB + Redis) |
| `GET /docs` | Interactive OpenAPI documentation |
| `GET /redoc` | ReDoc API documentation |
| `GET /openapi.json` | Raw OpenAPI schema |

---

## 8. Run Tests

### Unit tests (no DB/Redis required)

```bash
pytest tests/unit/ -v
```

### All tests with coverage

```bash
pytest --cov=backend --cov-report=term-missing
```

### Run only integration tests (requires running DB + Redis)

```bash
pytest tests/integration/ -v -m integration
```

> **Note:** Integration tests are skipped by default. Remove the `@pytest.mark.skip`
> decorator in the test file to enable them when you have services running.

---

## 9. Linting and Formatting

```bash
# Check lint errors
ruff check .

# Auto-fix lint errors
ruff check . --fix

# Check formatting
ruff format . --check

# Apply formatting
ruff format .
```

---

## 10. Using Docker Compose for Everything

To run the full Phase 1 stack (API + PostgreSQL + Redis) in Docker:

> **Requires Docker Desktop to be installed.**

```bash
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View API logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop and delete volumes (resets all data)
docker-compose down -v
```

After starting, apply migrations:

```bash
# Run migrations against the Dockerized database
docker-compose exec api alembic upgrade head
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'backend'`**
→ Ensure your virtual environment is active: `source .venv/bin/activate`
→ Ensure you installed in editable mode: `uv pip install -e ".[dev]"`

**`asyncpg.exceptions.InvalidCatalogNameError: database "synapseops" does not exist`**
→ The database was not created. `POSTGRES_DB` in your `.env` must match the PostgreSQL database.
→ With Docker Compose, the DB is created automatically from `POSTGRES_DB`.

**`ConnectionRefusedError` for Redis**
→ Redis is not running. Start it: `docker-compose up -d redis`

**Alembic `FAILED: Can't locate revision identified by ...`**
→ Your migration history is inconsistent. Run `alembic history` to inspect.
→ If starting fresh: `docker-compose down -v && docker-compose up -d postgres && alembic upgrade head`
