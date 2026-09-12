import abc

from backend.core.logging import get_logger
from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult
from backend.intelligence.recovery.models import RecoveryPlan

logger = get_logger(__name__)


class RecoveryPlanner(abc.ABC):
    """Abstract Base Class for generating a RecoveryPlan from incident reasoning."""

    @abc.abstractmethod
    async def generate_plan(
        self,
        reasoning: IncidentReasoningResult,
        context: IncidentContext,
    ) -> RecoveryPlan:
        """Analyze reasoning and generate a structured recovery plan."""
        pass


class PlanValidator:
    """Deterministic application-level validator for recovery plans.

    Ensures that generated plans (especially those from AI) strictly adhere
    to safe boundaries, known topologies, and bounded actions.
    """

    def validate(self, plan: RecoveryPlan, context: IncidentContext) -> RecoveryPlan:
        """Validates the plan and mutates it (e.g., stripping bad steps) if necessary.

        Args:
            plan: The unvalidated plan.
            context: The original incident context containing the known topology.

        Returns:
            The validated and potentially sanitized plan.
        """
        valid_steps = []
        for step in plan.steps:
            if step.target_component not in context.topology_nodes:
                logger.warning(
                    "plan_validation_failed",
                    reason="target_component_not_in_topology",
                    step_id=step.step_id,
                    target_component=step.target_component,
                )
                continue

            # The action_type is already validated by Pydantic to be within RecoveryActionType.

            valid_steps.append(step)

        plan.steps = valid_steps
        plan.is_validated = True

        logger.info("plan_validated", plan_id=plan.plan_id, valid_steps=len(valid_steps))

        return plan
