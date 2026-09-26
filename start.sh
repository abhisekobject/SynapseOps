#!/usr/bin/env bash
# =============================================================================
# SynapseOps — One-Command Full-System Launcher
#
# Usage:
#   ./start.sh
#
# What this script starts:
#   1. Infrastructure (via Docker Compose)
#      - PostgreSQL       :5432
#      - Redis            :6379
#      - Prometheus       :9090
#      - Grafana          :3000
#      - Jaeger           :16686 (UI)  :4317 (OTLP gRPC)
#      - Simulation services:
#          sim-gateway    :8100
#          sim-api        :8101
#          sim-worker     :8102
#   2. Database migrations (Alembic)   — host process via .venv
#   3. Backend (FastAPI/uvicorn)        — host process via .venv  :8000
#   4. Frontend (Next.js)              — host process via npm     :3001
#
# Notes:
#   - All services run in dependency order with bounded health checks.
#   - Ctrl+C performs graceful cleanup of processes started by this script.
#   - Docker Compose manages all infrastructure; this script only starts
#     host-side processes (backend, frontend) directly.
#   - Frontend is started on port 3001 to avoid conflict with Grafana (:3000).
#
# Prerequisites:
#   - Docker Desktop (for all infrastructure + simulation services)
#   - Python virtual environment at .venv/  (uv venv .venv; uv pip install -e .[dev])
#   - Node.js and npm  (for frontend)
#   - .env file configured  (copy from .env.example)
#
# Logs:
#   .runtime/logs/backend.log
#   .runtime/logs/frontend.log
#
# PIDs:
#   .runtime/pids/backend.pid
#   .runtime/pids/frontend.pid
#
# Stop:
#   Press Ctrl+C — the script will clean up gracefully.
# =============================================================================

set -Eeuo pipefail

# =============================================================================
# SCRIPT IDENTITY — resolve project root from script location regardless of
# the directory the user invoked the script from.
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"

# =============================================================================
# CONSTANTS — colours and formatting
# =============================================================================
# Use tput if available, otherwise fall back to plain text.
if command -v tput &>/dev/null && tput setaf 1 &>/dev/null; then
  RED=$(tput setaf 1)
  GREEN=$(tput setaf 2)
  YELLOW=$(tput setaf 3)
  CYAN=$(tput setaf 6)
  BOLD=$(tput bold)
  RESET=$(tput sgr0)
else
  RED=""
  GREEN=""
  YELLOW=""
  CYAN=""
  BOLD=""
  RESET=""
fi

# =============================================================================
# LOGGING HELPERS
# =============================================================================
log_info()    { echo "${CYAN}[INFO]${RESET}  $*"; }
log_ok()      { echo "${GREEN}[OK]${RESET}    $*"; }
log_warn()    { echo "${YELLOW}[WARN]${RESET}  $*"; }
log_error()   { echo "${RED}[ERROR]${RESET} $*" >&2; }
log_section() { echo; echo "${BOLD}${CYAN}=== $* ===${RESET}"; echo; }

# =============================================================================
# CONFIGURATION — ports and timeouts
#
# These defaults are derived directly from .env / docker-compose.yml.
# They can be overridden by environment variables before running start.sh.
# =============================================================================

# Load .env if present (do NOT export secrets)
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # Read key=value pairs, skip comments and blank lines, do NOT print values.
  # We source it directly so the settings are available to child-process
  # environment construction later.  set -a ensures they are exported.
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

# ---------------------------------------------------------------------------
# Port resolution — read from environment (populated by .env above) or use
# the same defaults that docker-compose.yml uses.
# ---------------------------------------------------------------------------
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"
API_PORT="${API_PORT:-8000}"
API_HOST="${API_HOST:-0.0.0.0}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"
JAEGER_UI_PORT="${JAEGER_UI_PORT:-16686}"
JAEGER_OTLP_PORT="${JAEGER_OTLP_PORT:-4317}"
SIM_GATEWAY_PORT="${SIM_GATEWAY_PORT:-8100}"
SIM_API_PORT="${SIM_API_PORT:-8101}"
SIM_WORKER_PORT="${SIM_WORKER_PORT:-8102}"

# Next.js default port is 3000, but Grafana already uses 3000 (docker-compose).
# Therefore we start Next.js on 3001 unconditionally to avoid the conflict.
FRONTEND_PORT="${FRONTEND_PORT:-3001}"

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
INFRA_STARTUP_TIMEOUT="${INFRA_STARTUP_TIMEOUT:-90}"    # seconds to wait for Docker Compose healthy
DB_READY_TIMEOUT="${DB_READY_TIMEOUT:-60}"              # seconds to wait for PostgreSQL
REDIS_READY_TIMEOUT="${REDIS_READY_TIMEOUT:-30}"        # seconds to wait for Redis
BACKEND_READY_TIMEOUT="${BACKEND_READY_TIMEOUT:-60}"    # seconds to wait for backend /health/live
SIM_READY_TIMEOUT="${SIM_READY_TIMEOUT:-60}"            # seconds to wait for simulation services
HEALTHCHECK_INTERVAL="${HEALTHCHECK_INTERVAL:-2}"       # seconds between retry probes

# =============================================================================
# PID AND LOG MANAGEMENT
# =============================================================================
RUNTIME_DIR="${PROJECT_ROOT}/.runtime"
LOG_DIR="${RUNTIME_DIR}/logs"
PID_DIR="${RUNTIME_DIR}/pids"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"

BACKEND_PID=""
FRONTEND_PID=""

# Flag: did THIS invocation of start.sh start Docker Compose?
COMPOSE_STARTED_BY_US=false

# =============================================================================
# TRAP — graceful cleanup on Ctrl+C, SIGTERM, or unexpected exit
# =============================================================================
cleanup() {
  local exit_code=$?
  # Prevent re-entrant execution if cleanup triggers another EXIT.
  trap - EXIT SIGINT SIGTERM

  echo
  log_section "Shutting down SynapseOps"

  # Stop frontend (host process)
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    log_info "Stopping frontend (PID ${FRONTEND_PID})..."
    kill "${FRONTEND_PID}" 2>/dev/null || true
    # Wait up to 5 seconds for graceful exit.
    local waited=0
    while kill -0 "${FRONTEND_PID}" 2>/dev/null && [[ $waited -lt 5 ]]; do
      sleep 1
      ((waited++)) || true
    done
    if kill -0 "${FRONTEND_PID}" 2>/dev/null; then
      log_warn "Frontend did not exit gracefully; sending SIGKILL."
      kill -9 "${FRONTEND_PID}" 2>/dev/null || true
    fi
  fi
  rm -f "${FRONTEND_PID_FILE}" 2>/dev/null || true

  # Stop backend (host process)
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    log_info "Stopping backend (PID ${BACKEND_PID})..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    local waited=0
    while kill -0 "${BACKEND_PID}" 2>/dev/null && [[ $waited -lt 10 ]]; do
      sleep 1
      ((waited++)) || true
    done
    if kill -0 "${BACKEND_PID}" 2>/dev/null; then
      log_warn "Backend did not exit gracefully; sending SIGKILL."
      kill -9 "${BACKEND_PID}" 2>/dev/null || true
    fi
  fi
  rm -f "${BACKEND_PID_FILE}" 2>/dev/null || true

  # Stop Docker Compose services only if THIS invocation started them.
  if [[ "${COMPOSE_STARTED_BY_US}" == "true" ]]; then
    log_info "Stopping Docker Compose infrastructure..."
    if command -v docker &>/dev/null; then
      docker compose -f "${PROJECT_ROOT}/docker-compose.yml" stop 2>/dev/null || true
    fi
  fi

  echo
  log_ok "SynapseOps stopped cleanly."
  exit "${exit_code}"
}

trap cleanup EXIT SIGINT SIGTERM

# =============================================================================
# FAILURE REPORTING — call this when a required service fails to start
# =============================================================================
startup_failed() {
  local service="$1"
  local reason="$2"
  local log_file="${3:-}"

  echo
  echo "${RED}${BOLD}============================================================${RESET}"
  echo "${RED}${BOLD}              SYNAPSEOPS STARTUP FAILED${RESET}"
  echo "${RED}${BOLD}============================================================${RESET}"
  echo
  echo "  Failed service:  ${BOLD}${service}${RESET}"
  echo "  Reason:          ${reason}"
  if [[ -n "${log_file}" && -f "${log_file}" ]]; then
    echo "  Log file:        ${log_file}"
    echo
    echo "  Last 20 lines of log:"
    echo "  ─────────────────────────────────────────────────────────"
    tail -n 20 "${log_file}" | sed 's/^/  /'
    echo "  ─────────────────────────────────────────────────────────"
  fi
  echo
  echo "  Services started by this launcher are being stopped safely."
  echo "${RED}${BOLD}============================================================${RESET}"
  echo
  # cleanup() will be called automatically by the EXIT trap.
  exit 1
}

# =============================================================================
# UTILITY: Check whether a TCP port is currently listening.
# Returns 0 if occupied, 1 if free.
# =============================================================================
port_in_use() {
  local port="$1"
  # lsof is available on macOS; nc is also always available.
  if command -v lsof &>/dev/null; then
    lsof -i "TCP:${port}" -sTCP:LISTEN -t &>/dev/null
    return $?
  else
    # Fallback: nc -z exits 0 if connection succeeded.
    nc -z 127.0.0.1 "${port}" &>/dev/null
    return $?
  fi
}

# =============================================================================
# UTILITY: Get the PID (if any) listening on a port.
# =============================================================================
pid_on_port() {
  local port="$1"
  if command -v lsof &>/dev/null; then
    lsof -i "TCP:${port}" -sTCP:LISTEN -t 2>/dev/null | head -1
  else
    echo ""
  fi
}

# =============================================================================
# UTILITY: Wait for an HTTP endpoint to return HTTP 200 (or any non-5xx
# response that indicates the service is alive).
# =============================================================================
wait_for_http() {
  local url="$1"
  local description="$2"
  local timeout="${3:-30}"
  local interval="${HEALTHCHECK_INTERVAL}"
  local elapsed=0

  log_info "Waiting for ${description} at ${url}..."
  while true; do
    local http_code
    http_code=$(curl --silent --output /dev/null --write-out "%{http_code}" \
                     --connect-timeout 2 --max-time 3 "${url}" 2>/dev/null) || http_code="000"

    if [[ "${http_code}" =~ ^(200|301|302|404)$ ]]; then
      log_ok "${description} responded (HTTP ${http_code})."
      return 0
    fi

    elapsed=$((elapsed + interval))
    if [[ ${elapsed} -ge ${timeout} ]]; then
      log_error "${description} did not become reachable within ${timeout}s (last HTTP: ${http_code})."
      return 1
    fi
    sleep "${interval}"
  done
}

# =============================================================================
# UTILITY: Wait for a TCP port to be open (database / Redis).
# =============================================================================
wait_for_tcp() {
  local host="$1"
  local port="$2"
  local description="$3"
  local timeout="${4:-30}"
  local interval="${HEALTHCHECK_INTERVAL}"
  local elapsed=0

  log_info "Waiting for ${description} at ${host}:${port}..."
  while true; do
    if nc -z "${host}" "${port}" &>/dev/null 2>&1; then
      log_ok "${description} is accepting connections."
      return 0
    fi
    elapsed=$((elapsed + interval))
    if [[ ${elapsed} -ge ${timeout} ]]; then
      log_error "${description} did not become reachable within ${timeout}s."
      return 1
    fi
    sleep "${interval}"
  done
}

# =============================================================================
# UTILITY: Read a PID from a file and verify it belongs to a running process.
# Echos the PID on success; echos "" if the process is not running.
# =============================================================================
read_valid_pid() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    echo ""
    return
  fi
  local pid
  pid=$(cat "${pid_file}" 2>/dev/null || echo "")
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    echo "${pid}"
  else
    # Stale PID file — remove it.
    rm -f "${pid_file}" 2>/dev/null || true
    echo ""
  fi
}

# =============================================================================
# PRE-FLIGHT: Display header
# =============================================================================
echo
echo "${BOLD}${CYAN}============================================================${RESET}"
echo "${BOLD}${CYAN}              SYNAPSEOPS${RESET}"
echo "${BOLD}${CYAN}       Autonomous Infrastructure Intelligence${RESET}"
echo "${BOLD}${CYAN}============================================================${RESET}"
echo

log_section "Pre-flight checks"

# =============================================================================
# PRE-FLIGHT: Confirm we are at the repository root
# =============================================================================
if [[ ! -f "${PROJECT_ROOT}/pyproject.toml" ]] || [[ ! -f "${PROJECT_ROOT}/docker-compose.yml" ]]; then
  log_error "start.sh must be run from the SynapseOps repository root."
  log_error "Detected root: ${PROJECT_ROOT}"
  exit 1
fi
log_ok "Repository root confirmed: ${PROJECT_ROOT}"

# =============================================================================
# PRE-FLIGHT: Check required tools
# =============================================================================

# Docker — required for infrastructure + simulation services
DOCKER_AVAILABLE=false
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  DOCKER_AVAILABLE=true
  log_ok "Docker: $(docker --version 2>/dev/null | head -1)"
else
  DOCKER_AVAILABLE=false
  log_warn "Docker is not available or Docker daemon is not running."
  log_warn "Infrastructure services (PostgreSQL, Redis, Prometheus, Grafana,"
  log_warn "Jaeger, and simulation services) require Docker Desktop."
  log_warn ""
  log_warn "Without Docker, the backend will only start if PostgreSQL and"
  log_warn "Redis are reachable at their configured addresses."
  log_warn "Observability services (Prometheus, Grafana, Jaeger) and"
  log_warn "simulation services will NOT be available."
  log_warn ""
  log_warn "To install Docker Desktop: https://www.docker.com/products/docker-desktop/"
fi

# Python virtual environment — required for backend and migrations
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
VENV_UVICORN="${PROJECT_ROOT}/.venv/bin/uvicorn"
VENV_ALEMBIC="${PROJECT_ROOT}/.venv/bin/alembic"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  log_error ".venv/bin/python not found."
  log_error "Please create the virtual environment first:"
  log_error "  uv venv .venv --python 3.11"
  log_error "  uv pip install -e '.[dev]'"
  exit 1
fi
log_ok "Python virtual environment: ${VENV_PYTHON}"

if [[ ! -x "${VENV_UVICORN}" ]]; then
  log_error ".venv/bin/uvicorn not found."
  log_error "Please install dependencies: uv pip install -e '.[dev]'"
  exit 1
fi
log_ok "uvicorn: ${VENV_UVICORN}"

if [[ ! -x "${VENV_ALEMBIC}" ]]; then
  log_error ".venv/bin/alembic not found."
  log_error "Please install dependencies: uv pip install -e '.[dev]'"
  exit 1
fi
log_ok "alembic: ${VENV_ALEMBIC}"

# Node.js and npm — required for frontend
if ! command -v node &>/dev/null; then
  log_error "Node.js is not installed or not in PATH."
  log_error "Please install Node.js: https://nodejs.org/"
  exit 1
fi
log_ok "Node.js: $(node --version)"

if ! command -v npm &>/dev/null; then
  log_error "npm is not installed or not in PATH."
  exit 1
fi
log_ok "npm: $(npm --version)"

# Frontend node_modules — must exist (we do NOT auto-install).
if [[ ! -d "${PROJECT_ROOT}/frontend/node_modules" ]]; then
  log_error "frontend/node_modules not found."
  log_error "Please install frontend dependencies first:"
  log_error "  cd frontend && npm install"
  exit 1
fi
log_ok "Frontend node_modules: present"

# curl — required for health checks
if ! command -v curl &>/dev/null; then
  log_error "curl is not installed. curl is required for health checks."
  exit 1
fi
log_ok "curl: $(curl --version 2>/dev/null | head -1)"

# nc (netcat) — used for TCP port checks
if ! command -v nc &>/dev/null; then
  log_warn "nc (netcat) not found. TCP port checks will be limited."
fi

# =============================================================================
# PRE-FLIGHT: Check .env file
# =============================================================================
if [[ ! -f "${ENV_FILE}" ]]; then
  log_warn ".env file not found at ${ENV_FILE}"
  log_warn "The backend requires .env to be configured."
  log_warn "Copy .env.example to .env and configure at minimum POSTGRES_PASSWORD."
  log_warn "Continuing — backend may fail to start if .env is absent."
else
  log_ok ".env file: present"
  # Show configured keys — NEVER print values.
  if grep -q "OPENAI_API_KEY" "${ENV_FILE}" 2>/dev/null; then
    log_info "  OPENAI_API_KEY: configured"
  fi
  if grep -q "POSTGRES_PASSWORD" "${ENV_FILE}" 2>/dev/null; then
    log_info "  POSTGRES_PASSWORD: configured"
  fi
fi

# =============================================================================
# PRE-FLIGHT: Check for port conflicts on host-launched services only.
# Docker Compose manages its own ports; we only check backend and frontend.
# =============================================================================
log_section "Port conflict detection"

check_port_available() {
  local port="$1"
  local service_name="$2"
  local our_pid_file="${3:-}"

  if port_in_use "${port}"; then
    # Check if it is one of our own previously-launched services.
    if [[ -n "${our_pid_file}" ]]; then
      local existing_pid
      existing_pid=$(read_valid_pid "${our_pid_file}")
      if [[ -n "${existing_pid}" ]]; then
        local listening_pid
        listening_pid=$(pid_on_port "${port}")
        if [[ "${existing_pid}" == "${listening_pid}" ]]; then
          log_warn "${service_name} is already running on port ${port} (PID ${existing_pid})."
          echo "already_running"
          return
        fi
      fi
    fi
    log_error "Port ${port} is already in use by an unrelated process."
    log_error "SynapseOps cannot safely start ${service_name} on port ${port}."
    log_error "Stop the process occupying port ${port} and try again."
    log_error "  lsof -i TCP:${port} -sTCP:LISTEN"
    exit 1
  fi
  echo "available"
}

BACKEND_PORT_STATUS=$(check_port_available "${API_PORT}" "Backend" "${BACKEND_PID_FILE}")
FRONTEND_PORT_STATUS=$(check_port_available "${FRONTEND_PORT}" "Frontend" "${FRONTEND_PID_FILE}")

if [[ "${BACKEND_PORT_STATUS}" == "available" ]]; then
  log_ok "Backend port ${API_PORT}: available"
fi
if [[ "${FRONTEND_PORT_STATUS}" == "available" ]]; then
  log_ok "Frontend port ${FRONTEND_PORT}: available"
fi

# =============================================================================
# CREATE RUNTIME DIRECTORIES
# =============================================================================
mkdir -p "${LOG_DIR}" "${PID_DIR}"

# =============================================================================
# STEP 1: INFRASTRUCTURE — Docker Compose
# =============================================================================
log_section "Infrastructure (Docker Compose)"

if [[ "${DOCKER_AVAILABLE}" == "false" ]]; then
  log_warn "Skipping Docker Compose infrastructure (Docker not available)."
  log_warn "Proceeding — backend will fail unless PostgreSQL and Redis are"
  log_warn "already running externally at ${POSTGRES_HOST:-localhost}:${POSTGRES_PORT} and"
  log_warn "${REDIS_HOST:-localhost}:${REDIS_PORT}."
  COMPOSE_STARTED_BY_US=false
else
  COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

  # Check if infrastructure services are already running.
  if docker compose -f "${COMPOSE_FILE}" ps postgres 2>/dev/null | grep -q "running"; then
    log_info "Docker Compose services appear to be running already."
    log_info "Checking health status of infrastructure services..."
    COMPOSE_STARTED_BY_US=false
  else
    log_info "Starting Docker Compose infrastructure services..."
    log_info "(postgres, redis, prometheus, grafana, jaeger, sim-gateway, sim-api, sim-worker)"
    echo

    if ! docker compose -f "${COMPOSE_FILE}" up -d \
         postgres redis prometheus grafana jaeger \
         sim-gateway sim-api sim-worker 2>&1; then
      startup_failed "Docker Compose" "docker compose up failed. Check Docker Desktop is running."
    fi
    COMPOSE_STARTED_BY_US=true
    log_ok "Docker Compose services launched."
  fi
fi

# =============================================================================
# STEP 2: WAIT FOR PostgreSQL
# =============================================================================
log_section "Waiting for PostgreSQL"

DB_HOST="${POSTGRES_HOST:-localhost}"

if [[ "${DOCKER_AVAILABLE}" == "false" ]]; then
  if ! wait_for_tcp "${DB_HOST}" "${POSTGRES_PORT}" "PostgreSQL" "${DB_READY_TIMEOUT}"; then
    startup_failed "PostgreSQL" \
      "PostgreSQL not reachable at ${DB_HOST}:${POSTGRES_PORT} and Docker is not available."
  fi
else
  # Wait for Docker health check or TCP connectivity.
  elapsed=0
  log_info "Waiting for PostgreSQL container to become healthy (up to ${DB_READY_TIMEOUT}s)..."
  while true; do
    health=$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" ps \
             --format "{{.Health}}" postgres 2>/dev/null | tr -d ' \r\n' || echo "")
    if [[ "${health}" == "healthy" ]]; then
      log_ok "PostgreSQL container is healthy."
      break
    fi
    # Also try raw TCP as a fallback.
    if nc -z "${DB_HOST}" "${POSTGRES_PORT}" &>/dev/null 2>&1; then
      log_ok "PostgreSQL is accepting connections on port ${POSTGRES_PORT}."
      break
    fi
    elapsed=$((elapsed + HEALTHCHECK_INTERVAL))
    if [[ ${elapsed} -ge ${DB_READY_TIMEOUT} ]]; then
      startup_failed "PostgreSQL" \
        "Did not become healthy within ${DB_READY_TIMEOUT}s. Check: docker compose logs postgres"
    fi
    echo -n "."
    sleep "${HEALTHCHECK_INTERVAL}"
  done
fi

# =============================================================================
# STEP 3: WAIT FOR Redis
# =============================================================================
log_section "Waiting for Redis"

REDIS_HOST_ADDR="${REDIS_HOST:-localhost}"

if [[ "${DOCKER_AVAILABLE}" == "false" ]]; then
  if ! wait_for_tcp "${REDIS_HOST_ADDR}" "${REDIS_PORT}" "Redis" "${REDIS_READY_TIMEOUT}"; then
    startup_failed "Redis" \
      "Redis not reachable at ${REDIS_HOST_ADDR}:${REDIS_PORT} and Docker is not available."
  fi
else
  elapsed=0
  log_info "Waiting for Redis container to become healthy (up to ${REDIS_READY_TIMEOUT}s)..."
  while true; do
    health=$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" ps \
             --format "{{.Health}}" redis 2>/dev/null | tr -d ' \r\n' || echo "")
    if [[ "${health}" == "healthy" ]]; then
      log_ok "Redis container is healthy."
      break
    fi
    if nc -z "${REDIS_HOST_ADDR}" "${REDIS_PORT}" &>/dev/null 2>&1; then
      log_ok "Redis is accepting connections on port ${REDIS_PORT}."
      break
    fi
    elapsed=$((elapsed + HEALTHCHECK_INTERVAL))
    if [[ ${elapsed} -ge ${REDIS_READY_TIMEOUT} ]]; then
      startup_failed "Redis" \
        "Did not become healthy within ${REDIS_READY_TIMEOUT}s. Check: docker compose logs redis"
    fi
    echo -n "."
    sleep "${HEALTHCHECK_INTERVAL}"
  done
fi

# =============================================================================
# STEP 4: DATABASE MIGRATIONS (Alembic)
# =============================================================================
log_section "Database migrations"

log_info "Running: alembic upgrade head"
# Run from project root (alembic.ini location) with POSTGRES_HOST set to localhost.
# When the backend runs on the host, it uses localhost, not the docker service name.
if ! (cd "${PROJECT_ROOT}" && POSTGRES_HOST="${DB_HOST}" \
      "${VENV_ALEMBIC}" upgrade head 2>&1); then
  startup_failed "Alembic" \
    "Database migration failed. Run 'alembic upgrade head' manually for details."
fi
log_ok "Database migrations applied."

# =============================================================================
# STEP 5: BACKEND (FastAPI / uvicorn)
# =============================================================================
log_section "Backend"

if [[ "${BACKEND_PORT_STATUS}" == "already_running" ]]; then
  log_info "Backend is already running. Verifying health..."
  if ! wait_for_http "http://localhost:${API_PORT}/health/live" "Backend liveness" 10; then
    startup_failed "Backend" \
      "Port ${API_PORT} is occupied but /health/live did not respond." \
      "${BACKEND_LOG}"
  fi
  BACKEND_PID=$(read_valid_pid "${BACKEND_PID_FILE}")
  log_ok "Backend already running (PID ${BACKEND_PID})."
else
  # Backend must reach localhost for postgres/redis — use the host-facing addresses.
  BACKEND_ENV=(
    "POSTGRES_HOST=${DB_HOST}"
    "POSTGRES_PORT=${POSTGRES_PORT}"
    "REDIS_HOST=${REDIS_HOST_ADDR}"
    "REDIS_PORT=${REDIS_PORT}"
    "SIM_GATEWAY_URL=http://localhost:${SIM_GATEWAY_PORT}"
    "SIM_API_URL=http://localhost:${SIM_API_PORT}"
    "SIM_WORKER_URL=http://localhost:${SIM_WORKER_PORT}"
    "OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:${JAEGER_OTLP_PORT}"
    "OTEL_EXPORTER_OTLP_INSECURE=true"
  )

  log_info "Starting backend on port ${API_PORT}..."
  log_info "Log: ${BACKEND_LOG}"

  # Launch uvicorn in the background.
  # We do NOT use --reload in demo mode — keep it stable and predictable.
  (
    cd "${PROJECT_ROOT}"
    env "${BACKEND_ENV[@]}" \
      "${VENV_UVICORN}" backend.main:app \
        --host "${API_HOST}" \
        --port "${API_PORT}" \
        --log-level info
  ) >> "${BACKEND_LOG}" 2>&1 &

  BACKEND_PID=$!
  echo "${BACKEND_PID}" > "${BACKEND_PID_FILE}"
  log_info "Backend process launched (PID ${BACKEND_PID})."

  # Wait for liveness.
  if ! wait_for_http \
       "http://localhost:${API_PORT}/health/live" \
       "Backend liveness" \
       "${BACKEND_READY_TIMEOUT}"; then
    startup_failed "Backend" \
      "Liveness check timed out after ${BACKEND_READY_TIMEOUT}s." \
      "${BACKEND_LOG}"
  fi

  # Wait for readiness (DB + Redis connected).
  log_info "Checking backend readiness (DB + Redis)..."
  elapsed=0
  while true; do
    ready_code=$(curl --silent --output /dev/null --write-out "%{http_code}" \
                      --connect-timeout 2 --max-time 3 \
                      "http://localhost:${API_PORT}/health/ready" 2>/dev/null) || ready_code="000"
    if [[ "${ready_code}" == "200" ]]; then
      log_ok "Backend is ready (HTTP 200 from /health/ready)."
      break
    fi
    elapsed=$((elapsed + HEALTHCHECK_INTERVAL))
    if [[ ${elapsed} -ge ${BACKEND_READY_TIMEOUT} ]]; then
      startup_failed "Backend" \
        "/health/ready returned ${ready_code} after ${BACKEND_READY_TIMEOUT}s. Possible DB/Redis issue." \
        "${BACKEND_LOG}"
    fi
    sleep "${HEALTHCHECK_INTERVAL}"
  done
fi

# =============================================================================
# STEP 6: SIMULATION SERVICES — verify (Docker Compose already started them)
# =============================================================================
log_section "Simulation services"

if [[ "${DOCKER_AVAILABLE}" == "false" ]]; then
  log_warn "Simulation services unavailable (Docker not running)."
else
  elapsed=0
  SIM_ALL_READY=true
  log_info "Waiting for simulation services (up to ${SIM_READY_TIMEOUT}s)..."

  for sim_port in "${SIM_GATEWAY_PORT}" "${SIM_API_PORT}" "${SIM_WORKER_PORT}"; do
    case "${sim_port}" in
      "${SIM_GATEWAY_PORT}") sim_name="sim-gateway" ;;
      "${SIM_API_PORT}")     sim_name="sim-api"     ;;
      "${SIM_WORKER_PORT}")  sim_name="sim-worker"  ;;
      *)                     sim_name="sim-unknown" ;;
    esac

    if ! wait_for_http \
         "http://localhost:${sim_port}/health" \
         "${sim_name}" \
         "${SIM_READY_TIMEOUT}"; then
      log_warn "${sim_name} health check failed. It may still be starting."
      SIM_ALL_READY=false
    fi
  done

  if [[ "${SIM_ALL_READY}" == "true" ]]; then
    log_ok "All simulation services are healthy."
  else
    log_warn "Some simulation services may not yet be healthy."
    log_warn "Check: docker compose logs sim-gateway sim-api sim-worker"
  fi
fi

# =============================================================================
# STEP 7: OBSERVABILITY — verify (Docker Compose already started them)
# =============================================================================
log_section "Observability services"

if [[ "${DOCKER_AVAILABLE}" == "false" ]]; then
  log_warn "Observability services unavailable (Docker not running)."
  PROMETHEUS_READY=false
  GRAFANA_READY=false
  JAEGER_READY=false
else
  PROMETHEUS_READY=false
  GRAFANA_READY=false
  JAEGER_READY=false

  # Prometheus
  if wait_for_http "http://localhost:${PROMETHEUS_PORT}/-/healthy" "Prometheus" 30; then
    PROMETHEUS_READY=true
  else
    log_warn "Prometheus did not confirm healthy within 30s."
  fi

  # Grafana
  if wait_for_http "http://localhost:${GRAFANA_PORT}/api/health" "Grafana" 30; then
    GRAFANA_READY=true
  else
    log_warn "Grafana did not confirm healthy within 30s."
  fi

  # Jaeger
  if wait_for_http "http://localhost:${JAEGER_UI_PORT}/" "Jaeger" 30; then
    JAEGER_READY=true
  else
    log_warn "Jaeger did not confirm healthy within 30s."
  fi
fi

# =============================================================================
# STEP 8: FRONTEND (Next.js)
# =============================================================================
log_section "Frontend"

if [[ "${FRONTEND_PORT_STATUS}" == "already_running" ]]; then
  log_info "Frontend is already running on port ${FRONTEND_PORT}."
  if ! wait_for_http "http://localhost:${FRONTEND_PORT}" "Frontend" 10; then
    log_warn "Port ${FRONTEND_PORT} is occupied but the frontend did not respond."
  fi
  FRONTEND_PID=$(read_valid_pid "${FRONTEND_PID_FILE}")
  log_ok "Frontend already running (PID ${FRONTEND_PID})."
else
  # Next.js is started on FRONTEND_PORT (3001) to avoid conflict with Grafana (3000).
  # The frontend reads NEXT_PUBLIC_API_BASE_URL for the backend API base URL.
  NEXT_PUBLIC_API_BASE_URL="http://localhost:${API_PORT}/api/v1"

  log_info "Starting Next.js frontend on port ${FRONTEND_PORT}..."
  log_info "Backend API URL: ${NEXT_PUBLIC_API_BASE_URL}"
  log_info "Log: ${FRONTEND_LOG}"

  (
    cd "${PROJECT_ROOT}/frontend"
    NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL}" \
      npm run dev -- --port "${FRONTEND_PORT}" 2>&1
  ) >> "${FRONTEND_LOG}" 2>&1 &

  FRONTEND_PID=$!
  echo "${FRONTEND_PID}" > "${FRONTEND_PID_FILE}"
  log_info "Frontend process launched (PID ${FRONTEND_PID})."

  # Next.js takes a moment to compile on first start — wait for it.
  FRONTEND_READY=false
  elapsed=0
  FRONTEND_TIMEOUT=90
  log_info "Waiting for frontend to compile and become ready (up to ${FRONTEND_TIMEOUT}s)..."
  while true; do
    http_code=$(curl --silent --output /dev/null --write-out "%{http_code}" \
                     --connect-timeout 2 --max-time 5 \
                     "http://localhost:${FRONTEND_PORT}" 2>/dev/null) || http_code="000"
    if [[ "${http_code}" =~ ^(200|301|302)$ ]]; then
      FRONTEND_READY=true
      log_ok "Frontend is ready (HTTP ${http_code})."
      break
    fi
    # Check whether frontend process is still alive.
    if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
      startup_failed "Frontend" \
        "Frontend process exited unexpectedly." \
        "${FRONTEND_LOG}"
    fi
    elapsed=$((elapsed + HEALTHCHECK_INTERVAL))
    if [[ ${elapsed} -ge ${FRONTEND_TIMEOUT} ]]; then
      log_warn "Frontend did not become ready within ${FRONTEND_TIMEOUT}s."
      log_warn "It may still be compiling. Check: tail -f ${FRONTEND_LOG}"
      FRONTEND_READY=false
      break
    fi
    echo -n "."
    sleep "${HEALTHCHECK_INTERVAL}"
  done
fi

# =============================================================================
# STEP 9: FINAL HEALTH VERIFICATION
# =============================================================================
log_section "Final health verification"

# Backend liveness
BACKEND_FINAL_STATUS="READY"
if ! curl --silent --output /dev/null --write-out "%{http_code}" \
          --connect-timeout 2 --max-time 3 \
          "http://localhost:${API_PORT}/health/live" 2>/dev/null | grep -q "200"; then
  BACKEND_FINAL_STATUS="DEGRADED"
  log_warn "Backend /health/live did not return 200 at final check."
fi

# Backend readiness (DB + Redis)
ready_code=$(curl --silent --output /dev/null --write-out "%{http_code}" \
                  --connect-timeout 2 --max-time 3 \
                  "http://localhost:${API_PORT}/health/ready" 2>/dev/null) || ready_code="000"
if [[ "${ready_code}" != "200" ]]; then
  log_warn "Backend /health/ready returned ${ready_code}. DB or Redis may be unavailable."
fi

# Verify frontend → backend configuration
log_info "Verifying frontend → backend connectivity..."
backend_health=$(curl --silent --connect-timeout 3 --max-time 5 \
                      "http://localhost:${API_PORT}/health" 2>/dev/null) || backend_health=""
if echo "${backend_health}" | grep -q '"status"'; then
  log_ok "Backend health endpoint returned a valid response."
else
  log_warn "Backend /health did not return expected JSON. Check the backend log."
fi

log_ok "Final verification complete."

# =============================================================================
# STARTUP SUMMARY
# =============================================================================
echo
echo "${BOLD}${CYAN}============================================================${RESET}"
echo "${BOLD}${CYAN}                 SYNAPSEOPS READY${RESET}"
echo "${BOLD}${CYAN}============================================================${RESET}"
echo

# Determine status indicators.
ok_mark="${GREEN}READY${RESET}"
warn_mark="${YELLOW}CHECK LOGS${RESET}"
skip_mark="${YELLOW}UNAVAILABLE${RESET}"

printf "  %-28s %-40s %s\n" "SERVICE" "ADDRESS" "STATUS"
echo "  ──────────────────────────────────────────────────────────────────────────────"

# Frontend
if [[ "${FRONTEND_READY:-false}" == "true" ]]; then
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Frontend (Operations Console)" \
    "http://localhost:${FRONTEND_PORT}" "${ok_mark}"
else
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Frontend (Operations Console)" \
    "http://localhost:${FRONTEND_PORT}" "${warn_mark}"
fi

# Backend API
if [[ "${BACKEND_FINAL_STATUS}" == "READY" ]]; then
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Backend API" \
    "http://localhost:${API_PORT}" "${ok_mark}"
else
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Backend API" \
    "http://localhost:${API_PORT}" "${warn_mark}"
fi

# Backend Docs
printf "  %-28s %-40s\n" "  └─ API Docs" "http://localhost:${API_PORT}/docs"
printf "  %-28s %-40s\n" "  └─ Health" "http://localhost:${API_PORT}/health"
printf "  %-28s %-40s\n" "  └─ Readiness" "http://localhost:${API_PORT}/health/ready"
printf "  %-28s %-40s\n" "  └─ Metrics" "http://localhost:${API_PORT}/metrics"

echo "  ──────────────────────────────────────────────────────────────────────────────"

if [[ "${DOCKER_AVAILABLE}" == "true" ]]; then
  # Simulation services
  if [[ "${SIM_ALL_READY:-false}" == "true" ]]; then
    SIM_STATUS="${ok_mark}"
  else
    SIM_STATUS="${warn_mark}"
  fi
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Simulation Gateway" \
    "http://localhost:${SIM_GATEWAY_PORT}" "${SIM_STATUS}"
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Simulation API" \
    "http://localhost:${SIM_API_PORT}" "${SIM_STATUS}"
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Simulation Worker" \
    "http://localhost:${SIM_WORKER_PORT}" "${SIM_STATUS}"

  echo "  ──────────────────────────────────────────────────────────────────────────────"

  # Infrastructure
  printf "  %-28s %-40s\n" "PostgreSQL" "localhost:${POSTGRES_PORT}"
  printf "  %-28s %-40s\n" "Redis" "localhost:${REDIS_PORT}"

  echo "  ──────────────────────────────────────────────────────────────────────────────"

  # Observability
  if [[ "${PROMETHEUS_READY}" == "true" ]]; then
    printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Prometheus" \
      "http://localhost:${PROMETHEUS_PORT}" "${ok_mark}"
  else
    printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Prometheus" \
      "http://localhost:${PROMETHEUS_PORT}" "${warn_mark}"
  fi

  if [[ "${GRAFANA_READY}" == "true" ]]; then
    printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Grafana" \
      "http://localhost:${GRAFANA_PORT}" "${ok_mark}"
    printf "  %-28s %-40s\n" "  └─ Credentials" "admin / ${GRAFANA_ADMIN_PASSWORD:-admin}"
  else
    printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Grafana" \
      "http://localhost:${GRAFANA_PORT}" "${warn_mark}"
  fi

  if [[ "${JAEGER_READY}" == "true" ]]; then
    printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Jaeger" \
      "http://localhost:${JAEGER_UI_PORT}" "${ok_mark}"
  else
    printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Jaeger" \
      "http://localhost:${JAEGER_UI_PORT}" "${warn_mark}"
  fi
else
  printf "  ${BOLD}%-28s${RESET} %-40s %b\n" "Docker services" \
    "(postgres, redis, prometheus, grafana, jaeger, sim-*)" "${skip_mark}"
  log_warn "Install Docker Desktop to enable infrastructure and observability services."
fi

echo
echo "  ${BOLD}Logs:${RESET}"
printf "  %-28s %s\n" "  Backend" "${BACKEND_LOG}"
printf "  %-28s %s\n" "  Frontend" "${FRONTEND_LOG}"
echo
echo "${BOLD}${CYAN}============================================================${RESET}"
echo "${BOLD}${CYAN}  Open the Operations Console:${RESET}"
echo "${BOLD}${GREEN}  http://localhost:${FRONTEND_PORT}${RESET}"
echo
echo "${BOLD}${CYAN}  Backend API Documentation:${RESET}"
echo "${BOLD}${GREEN}  http://localhost:${API_PORT}/docs${RESET}"
echo "${BOLD}${CYAN}============================================================${RESET}"
echo
echo "  Press ${BOLD}Ctrl+C${RESET} to stop services started by this launcher."
echo "  SynapseOps-managed PIDs: backend=${BACKEND_PID}, frontend=${FRONTEND_PID}"
echo

# =============================================================================
# WAIT — keep the launcher alive so Ctrl+C works cleanly.
# All child processes run in the background; we wait indefinitely here.
# =============================================================================
wait
