# =============================================================================
# SynapseOps Backend — Dockerfile
# Multi-stage build for a clean, reproducible image.
# Stage 1 (builder): installs dependencies via uv
# Stage 2 (runtime): copies only the installed packages and app code
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv==0.12.5

WORKDIR /build

# Copy dependency specification first (maximizes layer cache reuse)
COPY pyproject.toml ./

# Install all production dependencies into a local .venv
# --no-dev: skip dev dependencies (ruff, pytest, etc.) in production image
RUN uv venv .venv && \
    uv pip install --python .venv/bin/python \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.9.0" \
    "pydantic-settings>=2.5.0" \
    "python-dotenv>=1.0.0" \
    "sqlalchemy>=2.0.0" \
    "asyncpg>=0.30.0" \
    "alembic>=1.13.0" \
    "redis[asyncio]>=5.1.0" \
    "structlog>=24.4.0" \
    "psycopg2-binary>=2.9.0"

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

# Create a non-root user for the application process
RUN groupadd --gid 1001 synapseops && \
    useradd --uid 1001 --gid synapseops --no-create-home synapseops

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application source
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Drop to non-root user
USER synapseops

EXPOSE 8000

# Start the FastAPI application via uvicorn
# Host/port are configurable via environment variables at runtime
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
