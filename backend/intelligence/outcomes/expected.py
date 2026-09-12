from backend.intelligence.recovery.actions import RecoveryActionType


class ExpectedOutcomeResolver:
    """Strict mapping that determines the *expected* state from a RecoveryActionType."""

    _EXPECTED_STATES: dict[RecoveryActionType, str] = {
        RecoveryActionType.RESTART_SERVICE: "HEALTHY",
        RecoveryActionType.SCALE_UP: "CAPACITY_INCREASED_AND_HEALTHY",
        RecoveryActionType.BLOCK_TRAFFIC: "TRAFFIC_BLOCKED",
    }

    @classmethod
    def resolve(cls, action_type: RecoveryActionType) -> str:
        """Resolves the expected outcome string for an action."""
        if action_type not in cls._EXPECTED_STATES:
            return "UNKNOWN_EXPECTED_STATE"
        return cls._EXPECTED_STATES[action_type]
