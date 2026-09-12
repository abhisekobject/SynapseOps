from backend.intelligence.recovery.actions import RecoveryActionType
from backend.intelligence.recovery.models import RecoveryPlan
from backend.intelligence.safety.models import (
    PolicyDecision,
    PolicyDecisionStatus,
)

# Simple explicit risk baseline mapped directly from Phase 8 actions
# Deny by default: If an action is not mapped here, it will be treated as UNKNOWN -> DENY.
ACTION_BASELINE_RISK = {
    RecoveryActionType.RESTART_SERVICE: "MEDIUM",
    RecoveryActionType.SCALE_UP: "LOW",
    RecoveryActionType.ROLLBACK_DEPLOYMENT: "HIGH",
    RecoveryActionType.CLEAR_CACHE: "MEDIUM",
    RecoveryActionType.BLOCK_TRAFFIC: "HIGH",
    RecoveryActionType.MANUAL_INTERVENTION_REQUIRED: "LOW", # Safety fallback is conceptually low risk
}


class PolicyEngine:
    """Deterministic Policy Engine to evaluate Recovery Plans."""

    POLICY_VERSION = "v1.0.0"

    def evaluate(self, plan: RecoveryPlan, plan_hash: str) -> PolicyDecision:
        """
        Evaluate the recovery plan deterministically.
        Any unknown risk or unrecognized action results in DENY.
        """
        # Deny-by-default initialization
        decision = PolicyDecisionStatus.DENY
        reasons = []
        max_risk = "LOW"

        # Risk ordering helper
        risk_weights = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        if not plan.steps:
            return PolicyDecision(
                decision_id="tmp", # Filled by persistence later or omitted if we just want the model
                plan_id=plan.plan_id,
                plan_hash=plan_hash,
                decision=PolicyDecisionStatus.DENY,
                policy_version=self.POLICY_VERSION,
                risk_level="UNKNOWN",
                reasons=["Plan has no steps."],
            )

        for step in plan.steps:
            # Re-verify action type just in case
            if step.action_type not in ACTION_BASELINE_RISK:
                return PolicyDecision(
                    decision_id="tmp",
                    plan_id=plan.plan_id,
                    plan_hash=plan_hash,
                    decision=PolicyDecisionStatus.DENY,
                    policy_version=self.POLICY_VERSION,
                    risk_level="UNKNOWN",
                    reasons=[f"Unknown or unsupported action type: {step.action_type}"],
                )

            baseline = ACTION_BASELINE_RISK[step.action_type]

            # AI risk estimations in the plan are purely informative.
            # The Policy Engine is authoritative for risk assessment.
            if risk_weights[baseline] > risk_weights.get(max_risk, 0):
                max_risk = baseline

        # Policy Rules
        if max_risk == "LOW":
            decision = PolicyDecisionStatus.ALLOW
            reasons.append("All actions are LOW risk and pre-authorized by policy.")
        elif max_risk == "MEDIUM":
            decision = PolicyDecisionStatus.REQUIRES_APPROVAL
            reasons.append("Plan contains MEDIUM risk actions. Human approval required.")
        elif max_risk == "HIGH":
            decision = PolicyDecisionStatus.REQUIRES_APPROVAL
            reasons.append("Plan contains HIGH risk actions. Human approval required.")
        else:
            decision = PolicyDecisionStatus.DENY
            reasons.append(f"Plan risk ({max_risk}) exceeds permitted thresholds or is unknown.")

        return PolicyDecision(
            decision_id="", # Assigned by database
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            decision=decision,
            policy_version=self.POLICY_VERSION,
            risk_level=max_risk,
            reasons=reasons,
        )
