# Engineering Principles — SynapseOps

These principles govern all architectural and implementation decisions in SynapseOps. They are not aspirational slogans — they are binding design rules. When a future decision conflicts with a principle, the principle takes precedence unless the principle itself is formally revised through the architecture decision process.

---

## Principle 1: Safety Before Autonomy

SynapseOps must never be designed around unrestricted autonomous infrastructure control.

The architecture permanently separates three concerns that must not be collapsed:

```
AI REASONING
    ↓
PROPOSED ACTION
    ↓
POLICY / SAFETY ENGINE
    ↓
AUTHORIZATION
    ↓
ACTION EXECUTOR
    ↓
VERIFICATION
```

The AI reasoning component — whether deterministic logic, ML models, or an LLM — proposes actions. It does **not** execute them directly.

The policy and authorization layer evaluates every proposed action independently of the reasoning that generated it. This separation must be preserved even when it adds latency or complexity.

**The LLM or reasoning component must never directly execute arbitrary infrastructure commands.**

This principle is inviolable throughout all phases of the project.

---

## Principle 2: Explainability

Whenever possible, SynapseOps must retain a structured explanation of its operational decisions.

For any significant decision, the system should be capable of providing:

| Field | Description |
|---|---|
| Observed signals | The telemetry that triggered the analysis |
| Hypotheses considered | What possible root causes were evaluated |
| Confidence | The estimated confidence in the selected hypothesis |
| Rejected alternatives | What was considered and why it was dismissed |
| Proposed actions | What recovery strategies were generated |
| Policy decision | Whether the action was authorized, rejected, or escalated |
| Execution result | What the action executor reported |
| Verification result | Whether the system returned to desired state |
| Outcome record | The stored historical record |

Explainability is not merely a user-interface concern. It is a safety property. Unexplainable autonomous infrastructure decisions are inherently unsafe.

---

## Principle 3: Evidence Before Action

The system should not act merely because an AI model produced a plausible-sounding suggestion.

All proposed actions must be grounded in:

- Measured telemetry signals
- Observed system state
- Event history
- Dependency graph information
- Policy and historical outcomes
- Explicit, verifiable action preconditions

If the evidence base is insufficient to justify an action, the action should be withheld and the incident should be escalated to human review.

"Plausible reasoning without evidence" is not grounds for autonomous action.

---

## Principle 4: Least Privilege

SynapseOps should have only the permissions strictly necessary for the specific actions it is authorized to perform.

This applies at every layer:

- **Infrastructure access**: Only the minimum required credentials and API scopes
- **Action scope**: Actions should be bounded to the affected component, not system-wide
- **Data access**: Only the telemetry and configuration required for its operational role
- **AI component access**: The LLM or reasoning layer must not have direct access to execution APIs

Do not design the system with broad root or admin access "for convenience." The principle of least privilege is a foundational safety constraint.

---

## Principle 5: Human Governance

Not all actions are equal in risk. SynapseOps must model action risk explicitly and route decisions accordingly.

### Conceptual Action-Risk Hierarchy

| Risk Level | Description | Authorization Model |
|---|---|---|
| **Low** | Reversible, bounded, high-confidence, frequently successful in similar past contexts | Potentially automatic under strict conditions |
| **Medium** | Partially reversible or moderate confidence or broader scope | Potentially automatic under stricter policy conditions |
| **High** | Low reversibility, broad impact, lower confidence, or affecting critical services | Requires explicit human authorization |
| **Critical / Destructive** | Irreversible, large blast radius, or data-affecting | Should not be autonomously executed without specialized, carefully designed authorization protocols |

Human operators must retain meaningful oversight. The system should be designed to make that oversight easy and well-informed, not to route around it.

The exact boundary between risk levels will be defined in Phase 9 (Safety / Policy / Human Approval).

---

## Principle 6: Reversibility

When multiple recovery strategies are available, prefer the one that is most reversible.

All recovery actions should ideally define:

| Property | Purpose |
|---|---|
| Rollback strategy | How to undo the action if it worsens the situation |
| Timeout | A maximum duration after which the action is considered failed |
| Blast radius | The bounded scope of the action's effect |
| Verification criteria | The observable conditions that indicate success or failure |

An action without a defined rollback strategy should be treated as higher risk than an equivalent action with one.

---

## Principle 7: Closed-Loop Verification

**"Action executed successfully" ≠ "System recovered."**

This distinction is critical and must be architecturally enforced.

Action execution success means: the action was submitted to the target system and was accepted without an immediate error.

System recovery means: the observable state of the infrastructure has returned to a healthy baseline as measured by telemetry.

SynapseOps must always pursue verification after action:

```
ACTION EXECUTED
    ↓
[Wait for observation window]
    ↓
OBSERVE ENVIRONMENT
    ↓
COMPARE TO HEALTHY BASELINE
    ↓
RECOVERY CONFIRMED → Record outcome
    OR
RECOVERY NOT CONFIRMED → Escalate / retry / rollback
```

---

## Principle 8: Deterministic Boundaries Around Probabilistic AI

AI and LLM components produce probabilistic output. Infrastructure execution must remain bounded by deterministic safeguards.

```
PROBABILISTIC REASONING (LLM / ML)
        ↓
STRUCTURED OUTPUT (validated schema)
        ↓
VALIDATION (preconditions, constraints)
        ↓
DETERMINISTIC POLICY (rules engine)
        ↓
AUTHORIZED EXECUTION (bounded action)
```

At no point should a probabilistic model's raw output directly control infrastructure without passing through structured validation and deterministic policy checks.

This principle prevents the most dangerous failure mode of AI-augmented operations: an AI model confidently generating a plausible but incorrect or dangerous action that is executed without sufficient constraint.

---

## Principle 9: Incremental Complexity

Do not introduce technologies simply because they are current, popular, or sophisticated.

Every technology, framework, or architectural pattern must have a clear, documented reason for its introduction.

### Default Posture: Start Simple

| Technology | Introduction Trigger |
|---|---|
| Kafka / message streaming | When event throughput or architectural decoupling requirements justify it |
| Kubernetes | When container orchestration provides real operational value |
| Graph database (Neo4j etc.) | When graph requirements exceed NetworkX or relational representations |
| Multiple microservices | When separation provides demonstrable architectural value |
| Deep learning (PyTorch etc.) | When simpler ML approaches are demonstrably insufficient |
| LLM API integration | When reasoning requirements exceed what deterministic or statistical methods can provide |

The failure mode to avoid is a system where most of the complexity exists to manage other complexity introduced prematurely, rather than to deliver operational intelligence.

See [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md) for the formal framework.

---

## Principle 10: Reproducibility

A core engineering goal is that another developer should be able to:

1. Clone the repository
2. Install documented prerequisites
3. Start the simulated infrastructure
4. Inject a defined failure scenario
5. Observe SynapseOps detect the failure
6. Observe the diagnostic hypothesis
7. Observe the recovery plan
8. Observe safe execution
9. Observe verification and outcome recording

This full end-to-end reproducibility is treated as a **first-class engineering requirement**, not an afterthought.

Reproducibility requires:

- Clear environment setup documentation
- Containerized infrastructure simulation
- Deterministic failure injection mechanisms
- Consistent telemetry baselines
- Automated test coverage of critical paths
- Documented expected outcomes for each failure scenario

---

## Principle Summary

| # | Principle | One-Line Statement |
|---|---|---|
| 1 | Safety Before Autonomy | AI reasons; policy authorizes; executor acts |
| 2 | Explainability | Every significant decision must be explainable |
| 3 | Evidence Before Action | Actions must be grounded in observed evidence |
| 4 | Least Privilege | Minimum necessary access at every layer |
| 5 | Human Governance | Risk-tiered authorization with human oversight for high-risk actions |
| 6 | Reversibility | Prefer reversible, bounded, verifiable actions |
| 7 | Closed-Loop Verification | Verify system recovery, not just action execution |
| 8 | Deterministic Boundaries | Probabilistic AI output must pass through deterministic safeguards |
| 9 | Incremental Complexity | Introduce complexity only when justified by requirements |
| 10 | Reproducibility | Full operational loop must be reproducible by a new developer |
