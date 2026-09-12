from enum import StrEnum


class RecoveryActionType(StrEnum):
    """The strictly bounded set of actions SynapseOps is permitted to reason about.

    By restricting actions to a predefined enum, we prevent the LLM from hallucinating
    arbitrary bash commands, SQL injections, or unsupported platform operations.
    """

    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    CLEAR_CACHE = "clear_cache"
    BLOCK_TRAFFIC = "block_traffic"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


class ActionRiskLevel(StrEnum):
    """The inherent risk level associated with executing a recovery action."""

    LOW = "LOW"        # e.g., scaling up (safe, additive)
    MEDIUM = "MEDIUM"  # e.g., restarting (temporary downtime)
    HIGH = "HIGH"      # e.g., rollback or blocking traffic (destructive or disruptive)


# Pre-defined metadata for the permitted actions.
# This guides the PlanValidator and helps the AI make safe decisions.
ACTION_REGISTRY = {
    RecoveryActionType.RESTART_SERVICE: {
        "description": "Restart a specific service to clear ephemeral faults or memory leaks.",
        "risk_level": ActionRiskLevel.MEDIUM,
    },
    RecoveryActionType.SCALE_UP: {
        "description": "Increase the replica count of a service to handle load.",
        "risk_level": ActionRiskLevel.LOW,
    },
    RecoveryActionType.ROLLBACK_DEPLOYMENT: {
        "description": "Revert to the previously known good deployment configuration.",
        "risk_level": ActionRiskLevel.HIGH,
    },
    RecoveryActionType.CLEAR_CACHE: {
        "description": "Flush cache entries for a given component.",
        "risk_level": ActionRiskLevel.MEDIUM,
    },
    RecoveryActionType.BLOCK_TRAFFIC: {
        "description": "Block external traffic routing to a failing component.",
        "risk_level": ActionRiskLevel.HIGH,
    },
    RecoveryActionType.MANUAL_INTERVENTION_REQUIRED: {
        "description": "No automated action is safe or applicable; escalate to humans.",
        "risk_level": ActionRiskLevel.LOW, # Escalating is safe, though the underlying incident is not.
    }
}
