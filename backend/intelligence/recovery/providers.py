import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult
from backend.intelligence.recovery.actions import (
    ACTION_REGISTRY,
    ActionRiskLevel,
    RecoveryActionType,
)
from backend.intelligence.recovery.core import RecoveryPlanner
from backend.intelligence.recovery.models import RecoveryPlan, RecoveryStep

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are the Recovery Planning engine for SynapseOps.

You receive:
1. Incident Reasoning (the AI's synthesis of the ongoing issue).
2. Incident Context (active events, known topology).
3. A strict Action Registry.

Your job is to construct a safe, minimal Recovery Plan using ONLY the permitted actions from the registry.

CRITICAL RULES:
1. You may ONLY output actions whose `action_type` exists exactly in the Action Registry.
2. The `target_component` must exactly match a component in the provided topology.
3. If no safe action exists, use `manual_intervention_required` and explain why.
4. Do NOT attempt to output shell commands, arbitrary SQL, or kubernetes commands in the justification or impact analysis.
"""


class MockRecoveryPlanner(RecoveryPlanner):
    """Deterministic mock provider for testing Recovery Planning."""

    async def generate_plan(
        self,
        reasoning: IncidentReasoningResult,
        context: IncidentContext,
    ) -> RecoveryPlan:
        logger.info("Generating mock recovery plan")

        target = reasoning.likely_root_causes[0] if reasoning.likely_root_causes else "unknown"

        step = RecoveryStep(
            action_type=RecoveryActionType.RESTART_SERVICE,
            target_component=target,
            justification="Mock deterministic recovery action.",
            estimated_risk=ActionRiskLevel.MEDIUM,
        )

        return RecoveryPlan(
            steps=[step] if target != "unknown" else [],
            overall_risk=ActionRiskLevel.MEDIUM if target != "unknown" else ActionRiskLevel.LOW,
            impact_analysis="Mock impact analysis.",
            created_at=datetime.now(UTC),
        )


class OpenAIRecoveryPlanner(RecoveryPlanner):
    """LLM-powered planner utilizing OpenAI structured outputs."""

    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(
            api_key=settings.ai_api_key or "mock-key",
            timeout=settings.ai_request_timeout_seconds,
            max_retries=1,
        )
        self.model = settings.ai_model

    async def generate_plan(
        self,
        reasoning: IncidentReasoningResult,
        context: IncidentContext,
    ) -> RecoveryPlan:
        logger.info("Generating OpenAI recovery plan")

        registry_context = {
            k.value: v for k, v in ACTION_REGISTRY.items()
        }

        prompt_payload = {
            "incident_reasoning": reasoning.model_dump(),
            "topology_nodes": context.topology_nodes,
            "action_registry": registry_context,
        }

        try:
            response: ChatCompletion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Input Data:\n{json.dumps(prompt_payload)}"},
                ],
                response_format=RecoveryPlan,
                temperature=0.1,
            )

            result = response.choices[0].message.parsed
            if not result:
                raise ValueError("Model refused to output structured plan.")

            return result

        except Exception as e:
            logger.error("OpenAI recovery planning failed", error=str(e))
            raise RuntimeError(f"Recovery planning unavailable due to provider error: {e}") from e
