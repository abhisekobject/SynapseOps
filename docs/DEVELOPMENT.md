# Development Philosophy — SynapseOps

---

## 1. Development Workflow

Every implementation phase follows this structured workflow:

```
INSPECT existing repository state
    ↓
UNDERSTAND previous implementation
    ↓
SPECIFY the requirements for this phase
    ↓
DESIGN the components and interfaces
    ↓
IMPLEMENT with clear modular structure
    ↓
TEST (unit, integration, and critical-path end-to-end)
    ↓
VALIDATE (run tests, check for regressions)
    ↓
DOCUMENT (update architecture and component docs)
    ↓
REVIEW (self-review for principle violations)
    ↓
COMMIT
```

No phase may skip any stage in this workflow. In particular:

- **Do not implement before understanding the existing state.** Each phase must begin by inspecting the current repository.
- **Do not commit untested changes.** Tests must pass before changes are committed.
- **Do not silently rewrite previous architecture.** If architectural changes are required, they must go through the formal ADR process.
- **Do not skip documentation updates.** If a component's behavior changes, its documentation must be updated in the same commit.

---

## 2. Phase Execution Rules

Every future implementation phase must:

1. **Inspect the existing repository** before making any changes
2. **Understand the previous implementation** — read relevant code, tests, and documentation
3. **Preserve working functionality** — do not break passing tests or working components
4. **Implement only the requested phase** — do not prematurely implement future phases
5. **Write tests** for all new logic
6. **Run all tests** and confirm they pass (including previous phase tests)
7. **Inspect for regressions** — run the full test suite, not just the new tests
8. **Update documentation** — README, ARCHITECTURE.md, component docs
9. **Verify integration** — confirm new components integrate with existing ones
10. **Report what was implemented** — provide a clear summary of what was built and tested

---

## 3. Coding Standards

### 3.1 Language and Style

- **Python version**: 3.11+ with full type annotations
- **Linting/formatting**: Ruff (replaces black + flake8 + isort)
- **Type checking**: mypy (introduced in later phases)
- **Line length**: 100 characters maximum (configured in Ruff)
- **Imports**: Organized (standard library → third party → local) by Ruff

### 3.2 Architecture Principles in Code

**Modular structure**: Each logical component lives in its own module or package. Files should have a single, clear responsibility.

```
✅  backend/intelligence/detection/anomaly_detector.py  (focused)
❌  backend/main.py  (everything in one file)
```

**Separation of concerns**: Data models, business logic, data access, and API handlers live in separate layers.

```
✅  models/  →  schemas/  →  services/  →  api/
❌  API handler directly queries database and runs ML model
```

**Explicit interfaces**: Components communicate through defined, typed interfaces (Pydantic models, typed function signatures). Implicit coupling via shared mutable state is avoided.

**Dependency injection**: FastAPI's built-in dependency injection is used for database sessions, service instances, and configuration. This improves testability.

**Configuration via environment variables**: All configuration is injected through environment variables, never hardcoded. Pydantic Settings manages configuration with validation.

### 3.3 Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Python module | `snake_case` | `anomaly_detector.py` |
| Python class | `PascalCase` | `AnomalyDetector` |
| Python function | `snake_case` | `detect_anomaly()` |
| Python variable | `snake_case` | `detection_result` |
| Pydantic model | `PascalCase` | `IncidentRecord` |
| FastAPI router | `snake_case` | `incidents_router` |
| Database table | `snake_case` | `incident_records` |
| Environment variable | `UPPER_SNAKE_CASE` | `DATABASE_URL` |
| TypeScript component | `PascalCase` | `IncidentCard` |
| TypeScript file | `kebab-case` | `incident-card.tsx` |

Names should be **meaningful and self-describing**. Avoid abbreviations that are not universally understood (`cfg`, `tmp`, `mgr` are acceptable; cryptic single-letter names are not, except in tightly scoped loops).

### 3.4 Documentation in Code

**Docstrings**: All public functions, classes, and modules must have docstrings. Google-style docstrings are preferred.

```python
def detect_anomaly(metric_series: list[float], window: int = 30) -> AnomalyResult:
    """Detect anomalies in a metric time series using statistical baseline comparison.

    Args:
        metric_series: Chronologically ordered list of metric values.
        window: Rolling window size in data points for baseline calculation.

    Returns:
        AnomalyResult containing detected anomalies and confidence scores.

    Raises:
        ValueError: If metric_series has fewer than window data points.
    """
```

**Inline comments**: Only for non-obvious design decisions, algorithmic choices, or known limitations. Do not comment the obvious.

```python
# Use isolation forest rather than z-score here because the distribution
# is heavily skewed by periodic batch jobs — see experiments/anomaly_baseline.ipynb
detector = IsolationForest(contamination=0.05)
```

### 3.5 Error Handling

- All I/O operations (database, external APIs, file system) must handle failures explicitly
- Use structured logging for all errors (see section 3.6)
- Do not swallow exceptions silently
- Use custom exception classes for domain-specific errors
- FastAPI exception handlers must return consistent, structured error responses

```python
# Bad
try:
    result = db.query(...)
except:
    pass  # silent failure

# Good
try:
    result = db.query(...)
except DatabaseConnectionError as e:
    logger.error("Database query failed", component="state_model", error=str(e))
    raise ServiceUnavailableError("System state unavailable") from e
```

### 3.6 Structured Logging

All logging must be structured (JSON or key-value pairs), not free-form strings. This makes logs machine-parseable and integrable with log analysis tools.

```python
# Bad
logger.info(f"Detected anomaly in service {service_name} at {timestamp}")

# Good
logger.info(
    "Anomaly detected",
    service=service_name,
    timestamp=timestamp,
    severity=anomaly.severity,
    metric=anomaly.metric_name,
    value=anomaly.observed_value,
    baseline=anomaly.baseline_value,
)
```

### 3.7 Security

- **No hardcoded secrets**: All API keys, passwords, and credentials are loaded from environment variables or a secrets manager
- **No secrets in version control**: `.env` files are in `.gitignore`. Use `.env.example` to document required variables
- **Input validation**: All external inputs (API requests, telemetry data) must be validated with Pydantic before processing
- **Least privilege**: Database users, service accounts, and API scopes have only the minimum permissions required

---

## 4. Testing Standards

### 4.1 Test Organization

```
tests/
├── unit/               # Isolated unit tests for individual functions and classes
├── integration/        # Tests involving multiple components or external dependencies (with mocking)
└── end_to_end/         # Full operational loop tests against simulated infrastructure
```

### 4.2 Test Requirements

- **All new logic must have unit tests** before the phase is considered complete
- **Critical paths must have integration tests**: anomaly detection → diagnosis → recovery plan → policy check is a critical path
- **End-to-end tests** are introduced in Phase 2+ when the simulator exists
- **Tests must pass before committing**
- **Test coverage for intelligence components** is particularly important; untested detection and diagnosis logic undermines system trustworthiness

### 4.3 Test Principles

- Tests should be **fast** (unit tests in milliseconds, integration tests in seconds)
- Tests should be **deterministic** (same input always produces same output)
- Tests should be **independent** (no test depends on another test's side effects)
- Use **factories** for test data, not hardcoded values
- Mock external dependencies (databases, LLMs, infrastructure APIs) in unit and integration tests

---

## 5. What to Avoid

| Anti-pattern | Why it's prohibited |
|---|---|
| Giant monolithic files | Violates separation of concerns; hard to test and maintain |
| Copy-pasted logic | Creates inconsistency and maintenance burden; use shared utilities |
| Magic constants | Use named constants or configuration values |
| Hardcoded credentials | Security violation |
| Silent exception handling | Hides failures; makes debugging difficult |
| Unnecessary abstractions | Adds complexity without value; wait until patterns are clear |
| Premature microservices | Distributed systems complexity before it's needed |
| Premature optimization | Optimize only with measured evidence of performance problems |
| Unnecessary dependencies | Every dependency adds maintenance burden, security surface, and potential breakage |
| Future phase implementation | Implement only what the current phase requires |

---

## 6. Commit Standards

Commit messages should follow Conventional Commits format:

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`

Examples:

```
feat(detection): add statistical baseline anomaly detector

Implements z-score based anomaly detection with rolling window baseline.
Includes unit tests for normal and anomalous series.

Refs: Phase 5
```

```
docs(architecture): update component spec for verification engine
```

---

## 7. Architectural Discipline

Future phases must not casually change fundamental architecture. If implementation experience suggests that an architectural decision was wrong, the correction path is:

1. Identify the specific problem
2. Propose a solution via Architecture Decision Record
3. Review the ADR against all engineering principles
4. Update architecture documentation
5. Implement the change with explicit migration strategy

Architectural drift — where individual commits gradually diverge from documented architecture without explicit decision — is prohibited.
