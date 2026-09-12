from backend.intelligence.execution.adapters import (
    ExecutionAdapter,
    SimulatedBlockTrafficExecutor,
    SimulatedRestartServiceExecutor,
    SimulatedScaleUpExecutor,
)
from backend.intelligence.recovery.actions import RecoveryActionType


class ExecutorRegistry:
    """Explicit mapping from allowed action types to capability-based adapters."""

    _registry: dict[RecoveryActionType, ExecutionAdapter] = {
        RecoveryActionType.SCALE_UP: SimulatedScaleUpExecutor(),
        RecoveryActionType.RESTART_SERVICE: SimulatedRestartServiceExecutor(),
        RecoveryActionType.BLOCK_TRAFFIC: SimulatedBlockTrafficExecutor(),
    }

    @classmethod
    def get_executor(cls, action_type: RecoveryActionType) -> ExecutionAdapter:
        """Retrieves the executor for a given action. Raises ValueError if unsupported."""
        if action_type not in cls._registry:
            raise ValueError(f"Unsupported action type: {action_type}. Execution rejected.")
        return cls._registry[action_type]
