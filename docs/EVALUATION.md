# Evaluation Framework — SynapseOps

> **Status**: Conceptual framework. Evaluation infrastructure will be implemented progressively starting from Phase 5. Metrics listed here are targets; actual measurement begins when the corresponding components exist.

---

## 1. Evaluation Philosophy

SynapseOps is an experimental engineering project. Its effectiveness must be measured quantitatively, not asserted qualitatively.

The evaluation framework serves several purposes:

1. **Progress measurement**: Track how system capability improves across phases
2. **Component validation**: Confirm that individual components meet quality criteria before integration
3. **Research grounding**: Provide empirical data for the research questions in `RESEARCH.md`
4. **Honest reporting**: Enable honest, evidence-based description of what the system can and cannot do
5. **Regression detection**: Catch capability regressions when components are modified

All metrics are measured against **labeled scenarios** injected into the simulated infrastructure. The label is the ground truth: known root cause, known correct recovery action, known recovery outcome.

---

## 2. Evaluation Categories

### Category 1: Detection

Measures the anomaly detection layer's ability to correctly identify when and where something is wrong.

| Metric | Description | Target Phase |
|---|---|---|
| **Precision** | Of all raised anomalies, what fraction were real? `TP / (TP + FP)` | Phase 5 |
| **Recall** | Of all real anomalies, what fraction were detected? `TP / (TP + FN)` | Phase 5 |
| **F1 Score** | Harmonic mean of precision and recall | Phase 5 |
| **False Positive Rate** | Rate of anomaly signals raised on healthy infrastructure | Phase 5 |
| **Detection Latency** | Time from failure onset to anomaly detection | Phase 5 |
| **Multimodal Improvement** | F1 improvement of combined signals vs. metrics-only | Phase 5 |

**Evaluation method**: Run each failure scenario repeatedly. Record all anomaly signals with timestamps. Compare to ground truth failure injection timestamps and locations.

---

### Category 2: Diagnosis

Measures the root cause analysis layer's ability to correctly identify the origin of a detected incident.

| Metric | Description | Target Phase |
|---|---|---|
| **Root Cause Accuracy (Top-1)** | Fraction of incidents where the highest-ranked hypothesis is the true root cause | Phase 6 |
| **Root Cause Accuracy (Top-3)** | Fraction of incidents where the true root cause appears in top 3 hypotheses | Phase 6 |
| **Diagnosis Latency** | Time from anomaly detection to hypothesis generation | Phase 6 |
| **Confidence Calibration** | Does stated confidence correlate with actual accuracy? | Phase 6–7 |
| **Graph vs. No-Graph** | Root cause accuracy with and without dependency graph | Phase 6 |
| **LLM Reasoning Improvement** | Hypothesis quality with and without LLM synthesis | Phase 7 |
| **Hallucination Rate** | Fraction of LLM claims not grounded in provided evidence | Phase 7 |

**Evaluation method**: For each labeled scenario, extract the top-k hypotheses. Compare against known root cause. Score confidence estimates against empirical accuracy.

---

### Category 3: Recovery Planning

Measures the quality and appropriateness of generated recovery plans.

| Metric | Description | Target Phase |
|---|---|---|
| **Plan Correctness Rate** | Fraction of plans containing the correct recovery action in top position | Phase 8 |
| **Plan Relevance Rate** | Fraction of plans containing only relevant actions (no spurious actions) | Phase 8 |
| **Risk Assessment Accuracy** | Does estimated risk match actual action impact? | Phase 8–9 |
| **Action Ranking Quality** | NDCG (Normalized Discounted Cumulative Gain) of action rankings | Phase 8 |
| **Planning Latency** | Time from diagnosis to recovery plan generation | Phase 8 |

---

### Category 4: Recovery Execution

Measures the success rate of executed recovery actions.

| Metric | Description | Target Phase |
|---|---|---|
| **Recovery Success Rate** | Fraction of executed recovery plans that result in verified system recovery | Phase 10–11 |
| **Time to Recovery** | Total time from failure injection to verified recovery | Phase 11 |
| **Action Success Rate** | Fraction of executed actions that complete without execution-level failure | Phase 10 |
| **Rollback Rate** | Fraction of executed actions that trigger rollback due to failed verification | Phase 11 |
| **Unnecessary Action Rate** | Fraction of actions that were executed but were not needed | Phase 11 |
| **Mean Actions per Recovery** | Average number of actions required to achieve verified recovery | Phase 11 |

---

### Category 5: Safety

Measures how well the safety and authorization model performs.

| Metric | Description | Target Phase |
|---|---|---|
| **Unauthorized Action Rate** | Fraction of executed actions that should have been escalated to humans | Phase 9 |
| **Policy Violation Rate** | Fraction of decisions that violate defined policy rules | Phase 9 |
| **Unsafe Action Rate** | Fraction of executed actions that worsened system state | Phase 10 |
| **Human Escalation Rate** | Fraction of incidents escalated to human approval | Phase 9 |
| **Unnecessary Escalation Rate** | Fraction of escalations that an accurate autonomous decision could have handled | Phase 9 |
| **Audit Coverage** | Fraction of decisions that appear in the audit log | Phase 9 |

---

### Category 6: Autonomy

Measures the overall degree of autonomous operational capability.

| Metric | Description | Target Phase |
|---|---|---|
| **Autonomous Resolution Rate** | Fraction of incidents resolved without human intervention | Phase 11 |
| **Human Approval Required Rate** | Fraction of incidents requiring human approval for at least one action | Phase 11 |
| **Successful Verification Rate** | Fraction of executions where verification confirms recovery | Phase 11 |
| **Learning Improvement** | Measured improvement in key metrics across successive incident batches | Phase 11 |

---

### Category 7: System Performance

Measures operational characteristics of SynapseOps itself.

| Metric | Description | Target Phase |
|---|---|---|
| **End-to-End Latency** | Total time from failure onset to recovery plan generation | Phase 8 |
| **Full Loop Latency** | Total time from failure onset to verified recovery | Phase 11 |
| **API Latency (p50, p95, p99)** | Response time for key API endpoints | Phase 1+ |
| **Telemetry Ingestion Rate** | Metrics and events processed per second | Phase 3 |

---

## 3. Ground Truth and Labeled Scenarios

All detection and diagnosis metrics require ground truth. Ground truth is established through:

1. **Labeled failure injection**: Each failure scenario has a defined:
   - Root cause service
   - Failure type
   - Expected anomaly signals
   - Correct recovery action
   - Expected recovery verification criteria

2. **Scenario catalog**: Maintained in the simulator codebase. Each scenario is reproducible and documented.

3. **Evaluation harness**: An automated script that:
   - Starts healthy infrastructure
   - Injects a labeled failure
   - Waits for SynapseOps to respond
   - Captures all system decisions and timings
   - Computes evaluation metrics against ground truth

---

## 4. Reporting Standards

Evaluation results must be reported with:

- **Sample size**: How many scenario runs was each metric computed over?
- **Confidence intervals**: For key metrics, bootstrap confidence intervals (95%)
- **Scenario breakdown**: Metrics per failure type, not just aggregate
- **Failure mode analysis**: What failure patterns does the system handle poorly?
- **Comparison baseline**: Where applicable, compare against a simple baseline (threshold alerting, random selection)

**Do not report cherry-picked results.** Report results across all labeled scenarios in the scenario catalog.

---

## 5. Evaluation Does Not Mean Perfection

The goal of evaluation is honest characterization, not perfect scores.

A system with measured precision of 0.72 and recall of 0.81 on anomaly detection is more valuable to engineering progress than a system that claims "near-perfect detection" without measurement.

When limitations are discovered through evaluation, they should be:
1. Documented honestly in the system's README and capability description
2. Investigated to understand root causes
3. Addressed in future phases if within scope
4. Reported as open problems if not yet addressed

---

## 6. Metrics Not Yet Applicable

The following metrics are conceptual at Phase 0. They will be activated as the corresponding components are built:

- All detection metrics → Phase 5
- All diagnosis metrics → Phase 6–7
- All recovery planning metrics → Phase 8
- All safety metrics → Phase 9
- All execution and autonomy metrics → Phase 10–11
- All learning metrics → Phase 11
