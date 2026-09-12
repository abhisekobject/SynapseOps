import abc

from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult


class ReasoningProvider(abc.ABC):
    """Abstract Base Class for AI Incident Reasoning providers.

    This establishes the Phase 7 boundary: The provider consumes structured
    incident context and outputs a strictly validated IncidentReasoningResult.
    It does not execute infrastructure commands.
    """

    @abc.abstractmethod
    async def analyze(self, context: IncidentContext) -> IncidentReasoningResult:
        """Synthesize structured evidence into an incident interpretation.

        Args:
            context: Verified, structured system evidence.

        Returns:
            IncidentReasoningResult: The validated AI interpretation.

        Raises:
            Exception: If the provider fails, times out, or returns invalid data.
        """
        pass
