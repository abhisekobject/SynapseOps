# AI Design Philosophy — SynapseOps

> **Core principle**: AI is one component of SynapseOps, not the entire system. The intelligence of the system comes from combining deterministic engineering logic, statistical modeling, machine learning, graph reasoning, and generative AI — each applied where it is genuinely the best tool for the problem.

---

## 1. The Hybrid Intelligence Model

SynapseOps explicitly rejects two failed patterns in AI-augmented operations:

**Pattern A: "Just use an LLM"**
Route all telemetry to an LLM and ask it what to do. Simple to prototype; fundamentally unreliable for infrastructure operations. LLMs hallucinate, lack real-time infrastructure context, cannot reliably ground recommendations in specific measured evidence, and produce non-deterministic output that is unsafe to act on directly.

**Pattern B: "LLMs are not ready"**
Use only traditional alerting thresholds and runbooks. Missing the genuine value that structured AI reasoning can provide for complex, multi-signal, multi-service incident understanding.

SynapseOps takes a third path: **hybrid intelligence**, where each analytical problem is addressed by the most appropriate technique.

---

## 2. Three Categories of Intelligence

### Category A: Deterministic Intelligence

Problems where the correct answer can be computed from the inputs using logic, rules, or well-defined algorithms.

**Use cases in SynapseOps**:

| Component | Deterministic Logic |
|---|---|
| Health check evaluation | Service is healthy/degraded/failed based on defined thresholds |
| Policy engine | Action is authorized/denied based on defined rules |
| Action validation | Action preconditions are met or not met |
| Authorization check | Action risk level permits autonomous execution or not |
| Verification criteria | Recovery is confirmed or not based on metric thresholds |
| Audit logging | Every action is recorded unconditionally |
| Rate limiting | Action count within time window |

**Why deterministic**: These problems have correct, verifiable answers. Using AI where determinism is possible adds unreliability and reduces auditability. The policy engine must be deterministic — it is the last safety boundary before infrastructure execution.

### Category B: Statistical / ML Intelligence

Problems where the answer cannot be computed from a single observation, but patterns in historical data can produce reliable, measurable predictions.

**Use cases in SynapseOps**:

| Component | Statistical / ML Approach |
|---|---|
| Anomaly detection | Statistical baseline modeling (z-score, rolling mean/std) |
| Anomaly detection (complex) | Isolation forest, autoencoders, LSTM time series models |
| Behavior modeling | Establish normal service behavior patterns |
| Failure prediction | Trend analysis, regression on degradation signals |
| Incident classification | Classify incident type from telemetry features |

**Why ML**: These problems involve pattern recognition in high-dimensional data where hand-crafted rules would be brittle and unmaintainable. ML models can learn from historical telemetry what "normal" looks like and what deviations warrant attention.

**Constraints on ML**:
- ML model outputs must be treated as probabilistic, not authoritative
- Confidence scores must be produced where possible
- Models must be evaluated against ground truth on historical incidents
- Models should be interpretable where possible, not black boxes
- ML outputs must pass through deterministic validation before influencing actions

### Category C: Generative / Reasoning Intelligence

Problems that require synthesizing multiple pieces of heterogeneous evidence into a coherent explanation, hypothesis, or natural-language output.

**Use cases in SynapseOps**:

| Component | Generative / Reasoning AI |
|---|---|
| Incident interpretation | Synthesize metrics, logs, events into a coherent incident narrative |
| Hypothesis generation | Propose root cause explanations given observed evidence |
| Evidence synthesis | Correlate multiple signals into a unified assessment |
| Recovery plan generation | Propose candidate actions with reasoning |
| Explanation generation | Generate operator-readable explanations of system decisions |
| Diagnosis assistance | Reason about complex multi-service failure cascades |

**Why LLM**: These problems involve understanding and reasoning across heterogeneous, natural-language-adjacent data (logs, event descriptions, service names, error messages). Structured ML models are not well-suited to this. LLMs, with appropriate grounding and constraints, can provide genuine value for synthesizing complex operational context.

---

## 3. The AI Execution Boundary

This is the most critical architectural rule in the AI design:

```
AI REASONING OUTPUT
        ↓
SCHEMA VALIDATION (Pydantic)
        ↓
PRECONDITION CHECK (deterministic)
        ↓
POLICY ENGINE (deterministic rules)
        ↓
AUTHORIZATION (role/risk check)
        ↓
ACTION EXECUTOR (bounded)
```

**The LLM never directly calls infrastructure APIs.**

**The LLM never produces free-form shell commands that are executed.**

The LLM (or any AI component) produces **structured output** conforming to a defined Pydantic schema. That output is validated, checked against preconditions, evaluated by the policy engine, authorized through the risk model, and only then executed through the bounded action executor.

This means that even if an LLM produces a subtly incorrect or dangerous recommendation, it cannot bypass the policy and authorization layers. The deterministic safeguards remain in place regardless of AI output quality.

---

## 4. LLM Integration Principles

When LLM integration is introduced (Phase 7), the following principles apply:

### 4.1 Structured Output Only

All LLM calls must request structured output (JSON conforming to a Pydantic schema). Free-form text responses are used only for explanation fields, not for actionable content.

```python
# The LLM is asked to produce this structure:
class IncidentHypothesis(BaseModel):
    probable_root_cause: str
    affected_services: list[str]
    confidence: float  # 0.0 - 1.0
    supporting_evidence: list[str]
    rejected_alternatives: list[str]
    proposed_actions: list[RecoveryActionCandidate]
    explanation: str  # Human-readable, not actionable
```

### 4.2 Evidence Grounding

LLM prompts must include actual, measured telemetry data. The LLM must reason about specific observed values, not hypothesize without data.

### 4.3 No Credentials or Secrets in Prompts

LLM prompts must never contain API keys, passwords, database connection strings, or any sensitive infrastructure configuration.

### 4.4 Prompt as Engineering Artifact

LLM prompts are treated as first-class engineering artifacts — versioned, tested, documented, and reviewed like code.

### 4.5 Confidence Calibration

LLM confidence estimates must be calibrated against actual accuracy on historical incidents. Uncalibrated confidence values should not influence authorization decisions.

### 4.6 Fallback Behavior

If LLM reasoning fails (timeout, API error, schema validation failure, low confidence), the system must fall back gracefully — either to a simpler deterministic approach, or to human escalation. LLM unavailability must not cause the system to halt.

---

## 5. Where AI Should NOT Be Used

| Situation | Why AI is inappropriate |
|---|---|
| Health threshold evaluation | A metric is above threshold or it isn't — deterministic |
| Policy rule enforcement | Rules must be predictable and auditable — deterministic |
| Action authorization | Must be deterministic for safety |
| Audit logging | Must be unconditional and deterministic |
| Action execution | Bounded executor handles this deterministically |
| Verification against thresholds | Thresholds are deterministic |

The fundamental test: **"Can a correct answer be computed deterministically from the inputs?"** If yes, use deterministic logic. If not, consider statistical or AI approaches with appropriate constraints.

---

## 6. AI Quality and Safety Standards

Before AI/ML components can influence operational decisions, they must meet:

| Standard | Description |
|---|---|
| **Evaluation** | Performance measured on held-out historical data with precision, recall, and calibration metrics |
| **Explainability** | System can produce a human-readable explanation for any AI-influenced decision |
| **Graceful degradation** | AI component failure does not cause system failure; fallback behavior exists |
| **Auditability** | All AI inputs, outputs, and downstream decisions are logged |
| **Constraint compliance** | AI output passes deterministic validation before influencing any action |
| **Human override** | Operators can always override, correct, or reject AI-generated conclusions |

---

## 7. The Anti-Pattern to Avoid

> **"LLM wrapper for DevOps"**: A system where the primary "intelligence" is routing telemetry to an LLM with a prompt like "here are my metrics, what should I do?" and then executing whatever the LLM suggests.

This pattern fails because:
- LLMs lack real-time infrastructure context and will hallucinate
- LLM output is non-deterministic and cannot be reliably validated
- There is no safety boundary between reasoning and execution
- The system provides no real analytical capability beyond what the LLM already has
- Failures are opaque and non-explainable

SynapseOps is explicitly designed to be the opposite of this pattern. The LLM is one reasoning tool in a layered system of analytical capability, deterministic validation, and safety-constrained execution.
