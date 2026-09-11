# Research Direction — SynapseOps

> SynapseOps is primarily an engineering side project. However, it is designed from the beginning to enable rigorous experimentation and to make genuine contributions to the understanding of intelligent infrastructure operations. This document defines the research questions that SynapseOps is intended to explore.

---

## 1. Context

The boundary between software infrastructure operations and applied AI research is increasingly productive. A system like SynapseOps sits at the intersection of:

- **Distributed systems observability** — what can be measured and how
- **Anomaly detection and statistical learning** — what deviations from normal are meaningful
- **Graph-based reasoning** — how dependency topology informs failure analysis
- **LLM capabilities and limitations** — where generative AI genuinely helps vs. where it fails
- **Human-machine collaboration in high-stakes environments** — how to design appropriate autonomy
- **Systems reliability engineering** — what constitutes recovery and how to measure it

These are active research areas. SynapseOps will not resolve them, but it is designed to generate real experimental data and structured observations about them.

---

## 2. Primary Research Questions

The following questions guide SynapseOps' experimental direction. None of these are answered yet. They define the problems the system is being built to investigate.

---

### RQ1: Multimodal Telemetry for Anomaly Detection

**Question**: Can infrastructure anomalies be detected more reliably by combining metrics, logs, traces, and events than by analyzing any single signal type?

**Why it matters**: Most production anomaly detection systems operate on metrics alone. Logs, traces, and events contain complementary information that may reduce both false positives and false negatives.

**Experimental approach**:
- Inject labeled failure scenarios into the simulated infrastructure
- Compare detection performance (precision, recall, F1) across: metrics-only, logs-only, combined signals
- Evaluate whether multimodal approaches generalize across failure types

---

### RQ2: Dependency Graphs and Root Cause Accuracy

**Question**: How significantly does incorporating a service dependency graph improve root cause localization accuracy compared to signal-based analysis alone?

**Why it matters**: In distributed systems, the component exhibiting the most severe anomaly is often not the root cause — it is a downstream victim. Graph-based analysis may substantially improve root cause identification.

**Experimental approach**:
- Run root cause analysis with and without dependency graph information
- Compare root cause accuracy (top-1, top-k) across failure scenarios
- Quantify improvement from graph integration for cascading vs. isolated failures

---

### RQ3: Temporal Relationships in Diagnosis

**Question**: How does the temporal ordering of anomaly onset across services improve or degrade root cause diagnosis?

**Why it matters**: In cascading failures, the sequence in which services begin showing anomalies contains causal information. Temporal analysis may improve the distinction between root cause and downstream effect.

**Experimental approach**:
- Record anomaly onset timestamps for each service during injected cascades
- Evaluate whether temporal ordering correlates with dependency topology
- Assess whether temporal features improve root cause hypothesis ranking

---

### RQ4: LLM-Assisted Incident Reasoning

**Question**: Can LLM-based reasoning improve the quality of incident interpretation and hypothesis generation for complex, multi-service failures?

**Why it matters**: LLMs may provide value in synthesizing heterogeneous, unstructured evidence (logs, error messages, service names) into coherent hypotheses. However, they may also hallucinate or misinterpret infrastructure-specific context.

**Experimental approach**:
- Compare incident interpretations: LLM-generated vs. structured ML-only
- Evaluate hypothesis accuracy against ground truth for labeled scenarios
- Measure hallucination rate: claims not supported by provided evidence
- Assess LLM confidence calibration against actual accuracy

---

### RQ5: Safe Constraint of Autonomous Action

**Question**: What policy and authorization structures effectively constrain autonomous infrastructure action while preserving sufficient autonomy for the system to be operationally useful?

**Why it matters**: Overly restrictive policies reduce the system to a recommendation engine. Overly permissive policies introduce unacceptable risk. The right balance is not obvious and depends on action type, system state, and confidence.

**Experimental approach**:
- Define formal action risk taxonomy
- Measure false authorization rate: actions that were authorized but should not have been
- Measure unnecessary escalation rate: actions escalated to humans that could safely have been autonomous
- Evaluate different policy configurations against these dual objectives

---

### RQ6: Action Confidence Estimation

**Question**: Can the system produce reliable confidence estimates for proposed recovery actions, and do higher-confidence proposals correspond to higher recovery success rates?

**Why it matters**: Confidence estimates are central to the risk-tiered authorization model. If confidence does not correlate with success, it cannot be used as an authorization criterion.

**Experimental approach**:
- Record confidence estimates for all proposed recovery actions
- Track recovery success outcomes
- Compute calibration curves: does stated confidence match empirical success rate?
- Investigate what features are most predictive of action success

---

### RQ7: Learning from Recovery Outcomes

**Question**: Can accumulated incident-to-outcome records meaningfully improve future diagnostic and planning quality?

**Why it matters**: A system that learns from experience is more valuable than one with static behavior. But "learning" in infrastructure operations requires careful design to avoid reinforcing bad patterns.

**Experimental approach**:
- Accumulate incident records with outcomes across repeated simulated scenarios
- Measure whether diagnostic accuracy and recovery success rate improve over time
- Evaluate whether the learning mechanism generalizes across related but distinct failure types

---

### RQ8: Symptoms vs. Root Causes

**Question**: What features reliably distinguish root-cause services from downstream symptom services in a multi-service failure cascade?

**Why it matters**: This is one of the hardest problems in distributed systems diagnosis. Getting it wrong leads to treating symptoms rather than causes, extending recovery time.

**Experimental approach**:
- Analyze telemetry patterns for root-cause vs. downstream services across injected failure types
- Identify feature sets (temporal, topological, metric pattern) that discriminate
- Evaluate whether these features generalize across failure types

---

### RQ9: Human Feedback Integration

**Question**: How should human operator corrections and feedback affect the system's future recommendations?

**Why it matters**: Human operators have domain knowledge that the system lacks. Effective integration of their feedback could substantially improve system quality over time.

**Experimental approach**:
- Design a feedback capture schema (correction type, confidence adjustment, action rating)
- Implement feedback integration in the learning layer
- Measure the effect of feedback on future decisions in similar scenarios

---

### RQ10: Deterministic vs. AI Reasoning Boundary

**Question**: For which types of infrastructure incidents does AI/LLM reasoning provide measurable improvement over deterministic or statistical methods? Where does it not?

**Why it matters**: Using AI where deterministic methods are better wastes resources and introduces unreliability. Using only deterministic methods misses genuine AI value. The boundary should be empirically characterized, not assumed.

**Experimental approach**:
- Compare AI-augmented vs. purely deterministic diagnosis across failure type categories
- Measure diagnostic accuracy, latency, and reliability for each approach
- Identify incident characteristics that predict AI reasoning advantage

---

## 3. Experiment Infrastructure

SynapseOps is designed to support experiments through:

- **Labeled failure scenarios**: Each injected failure has a known root cause, enabling ground truth evaluation
- **Reproducible simulation**: The simulator produces consistent telemetry for repeated experiments
- **Outcome logging**: All system decisions and outcomes are persisted, enabling retrospective analysis
- **Jupyter notebooks**: ML experiments are developed in notebooks (Google Colab compatible) before integration
- **Evaluation framework**: Standard metrics (precision, recall, F1, calibration) are computed automatically

See [`EVALUATION.md`](EVALUATION.md) for the full evaluation framework.

---

## 4. Research Posture

SynapseOps approaches these questions with engineering rigor:

- Claims are grounded in measured data, not assumptions
- Results are reported with uncertainty (confidence intervals where appropriate)
- Limitations are documented honestly
- Negative results are recorded — knowing what doesn't work is valuable
- Experiments are reproducible from documented scenarios

The project does not claim to publish academic research. However, it is designed so that future academic contributions from this work are possible if results warrant it.
