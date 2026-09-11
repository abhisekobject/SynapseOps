# GitHub Repository Standards — SynapseOps

> This document defines the quality bar that the SynapseOps repository should meet as a GitHub portfolio project. It serves as a checklist for Phase 12 and as a guiding standard throughout development.

---

## 1. Why GitHub Quality Matters for This Project

SynapseOps is a portfolio project. Its GitHub repository will be read by:

- Potential employers evaluating technical depth and engineering discipline
- Other developers interested in infrastructure intelligence and AIOps
- Future collaborators who might contribute to or fork the project
- The project author when returning to it after extended breaks

A high-quality GitHub repository communicates:

> "The developer who built this thinks carefully about systems, writes clean code, explains their decisions, tests their work, and approaches complex problems with engineering rigor."

A low-quality repository — even with sophisticated underlying code — communicates the opposite.

---

## 2. Repository-Level Requirements

### 2.1 README

The root README must clearly and concisely answer these questions for a developer reading it for the first time:

| Question | Required Section |
|---|---|
| What is this project? | Project name, one-line description |
| What problem does it solve? | Problem definition |
| How does it work? | Architecture overview (with diagram) |
| Why is it designed this way? | Key design decisions or link to docs |
| How do I run it? | Quick setup guide (when implemented) |
| What can it currently do? | Current status and capabilities |
| Where is it going? | Roadmap summary |
| What are its limitations? | Honest limitations section |
| Is it safe to deploy? | Disclaimer / safety notice |

The README should be scannable: use headers, bullet points, and tables. It should not be a wall of prose.

### 2.2 Documentation Completeness

The `docs/` directory must contain complete, up-to-date documentation for:

- [ ] Project vision and problem definition
- [ ] System architecture with diagrams
- [ ] Engineering principles
- [ ] Development guide (how to contribute / develop)
- [ ] Technology stack with rationale
- [ ] AI design philosophy
- [ ] Safety model
- [ ] Development roadmap
- [ ] Glossary
- [ ] Research direction
- [ ] Evaluation framework and results (when available)
- [ ] Architecture decision records

### 2.3 Architecture Diagrams

The repository should eventually contain visual architecture diagrams:

- High-level system architecture
- Component interaction diagram
- Data flow diagram
- Service dependency graph example
- Safety architecture diagram

Diagrams should be maintained in a format that is readable on GitHub (Mermaid diagrams in Markdown, or image files committed to the repository).

### 2.4 Setup Instructions

When implementation begins, the repository must include:

- Prerequisites (OS, tools, versions)
- Step-by-step local setup instructions
- Environment variable documentation (`.env.example`)
- Docker Compose commands to start the system
- How to inject a failure scenario
- How to observe SynapseOps responding
- Common setup problems and solutions

Setup instructions must be tested end-to-end on a clean environment before being published.

### 2.5 Demo Instructions

Once the operational loop is functional:

- Documented demo scenarios with expected outputs
- Example screenshots or screen recordings
- Expected terminal output for key steps

### 2.6 Testing Guide

- How to run unit tests
- How to run integration tests
- How to run evaluation scenarios
- Expected test output

---

## 3. Code Quality Standards

The repository code must demonstrate:

| Standard | Evidence |
|---|---|
| **Modular structure** | Clear directory organization with focused modules |
| **Type annotations** | All Python functions and Pydantic models typed |
| **Docstrings** | All public APIs documented |
| **Linting compliance** | Zero Ruff errors on the main branch |
| **Test coverage** | All critical intelligence components have tests |
| **No hardcoded secrets** | No credentials, API keys, or passwords in code |
| **Configuration externalized** | `.env.example` documents all required variables |
| **Clean git history** | Meaningful commit messages, no debug commits on main |

---

## 4. Issue and PR Quality

When the repository is active:

- **Issues** use templates: bug report, feature request, research question
- **Pull requests** use a template referencing the relevant phase
- **Branch naming**: `phase-N/description` (e.g., `phase-5/isolation-forest-detector`)
- **Main branch** is protected: no direct pushes, tests must pass

---

## 5. GitHub Actions

Once the codebase is substantive enough:

| Workflow | When it runs |
|---|---|
| `test.yml` | On every PR: run full test suite |
| `lint.yml` | On every PR: run Ruff |
| `docker-build.yml` | On merge to main: validate Docker build |

---

## 6. Repository Honesty Standards

The repository must communicate its real status honestly.

### Do

- Clearly state that this is an experimental project
- Label capabilities as "intended," "planned," "implemented," or "evaluated"
- Publish evaluation results including limitations and failure cases
- Document known issues and open problems
- Version the README to match the current implementation phase

### Do Not

- Claim capabilities that have not been implemented and measured
- Use phrases like "fully autonomous," "human-level," "production-ready" without evidence
- Hide evaluation metrics that are below target
- Present design documentation as if it were implementation

---

## 7. Phase 12 Repository Checklist

Before declaring the project portfolio-ready:

**Documentation**
- [ ] README answers all six core questions
- [ ] Architecture diagrams are current and visual
- [ ] All `docs/` files are up to date with implementation
- [ ] Setup guide tested on clean environment
- [ ] Demo guide written and tested

**Code**
- [ ] Zero Ruff errors on main branch
- [ ] All critical components have tests
- [ ] No hardcoded secrets
- [ ] Docker build passes from clean state

**Evaluation**
- [ ] Detection metrics published with scenario breakdown
- [ ] Diagnosis metrics published
- [ ] Recovery metrics published
- [ ] Safety metrics published
- [ ] Limitations section honestly documents failure cases

**Demo**
- [ ] At least one complete demo scenario documented
- [ ] Screenshot or recording of operational loop
- [ ] Failure injection to recovery demonstration visible

**Repository**
- [ ] `.gitignore` complete
- [ ] `.env.example` up to date
- [ ] License file present
- [ ] `CHANGELOG.md` or equivalent
- [ ] GitHub Actions passing on main

---

## 8. What This Repository Should Communicate

A visitor who reads the SynapseOps repository should come away thinking:

> "This developer understands distributed systems and infrastructure operations deeply. They approached a genuinely hard problem thoughtfully — defining the architecture before building, designing safety into the system from the start, being honest about what's experimental vs. what works, and measuring what they built. The code is clean and the decisions are explained. This is the work of someone who takes engineering seriously."

That impression is built through: honest documentation, clean code, tested components, clearly explained decisions, and results reported with integrity.
