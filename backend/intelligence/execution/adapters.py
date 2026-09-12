import asyncio
from abc import ABC, abstractmethod


class ExecutionAdapter(ABC):
    """Abstract base class for all capability-based execution adapters."""

    @abstractmethod
    async def execute(self, target: str) -> bool:
        """
        Execute the action against the target.
        Returns True on success, False on failure.
        """
        pass


class SimulatedScaleUpExecutor(ExecutionAdapter):
    """Safely simulates scaling up a service."""

    async def execute(self, target: str) -> bool:
        # Simulate network/execution latency
        await asyncio.sleep(0.5)
        return True


class SimulatedRestartServiceExecutor(ExecutionAdapter):
    """Safely simulates restarting a service."""

    async def execute(self, target: str) -> bool:
        await asyncio.sleep(0.5)
        return True


class SimulatedBlockTrafficExecutor(ExecutionAdapter):
    """Safely simulates blocking traffic to a service."""

    async def execute(self, target: str) -> bool:
        await asyncio.sleep(0.5)
        return True
