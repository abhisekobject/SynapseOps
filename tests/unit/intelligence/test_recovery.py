
import pytest
from fastapi.testclient import TestClient

from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult
from backend.intelligence.recovery.actions import ActionRiskLevel, RecoveryActionType
from backend.intelligence.recovery.core import PlanValidator
from backend.intelligence.recovery.models import RecoveryPlan, RecoveryStep
from backend.intelligence.recovery.providers import MockRecoveryPlanner
from backend.main import app

client = TestClient(app)


def test_plan_validator_rejects_hallucinated_targets():
    # Setup context with valid nodes
    context = IncidentContext(
        analysis_window_minutes=15,
        topology_nodes=["sim-api", "sim-worker", "database"]
    )

    # Setup a plan with one valid step and one hallucinated step
    step1 = RecoveryStep(
        action_type=RecoveryActionType.RESTART_SERVICE,
        target_component="sim-api",
        justification="Legit action",
        estimated_risk=ActionRiskLevel.MEDIUM
    )
    step2 = RecoveryStep(
        action_type=RecoveryActionType.RESTART_SERVICE,
        target_component="imaginary-service",
        justification="Hallucinated target",
        estimated_risk=ActionRiskLevel.LOW
    )

    plan = RecoveryPlan(
        steps=[step1, step2],
        overall_risk=ActionRiskLevel.MEDIUM,
        impact_analysis="Impact"
    )

    validator = PlanValidator()
    validated_plan = validator.validate(plan, context)

    # The hallucinated step should be stripped out
    assert len(validated_plan.steps) == 1
    assert validated_plan.steps[0].target_component == "sim-api"
    assert validated_plan.is_validated is True


@pytest.mark.asyncio
async def test_mock_recovery_planner():
    reasoning = IncidentReasoningResult(
        summary="Incident summary",
        observed_facts=[],
        likely_root_causes=["database"],
        propagation_interpretation="Interpretation",
        uncertainty="",
        confidence="HIGH"
    )

    context = IncidentContext(
        analysis_window_minutes=15,
        topology_nodes=["database"]
    )

    planner = MockRecoveryPlanner()
    plan = await planner.generate_plan(reasoning, context)

    assert len(plan.steps) == 1
    assert plan.steps[0].target_component == "database"
    assert plan.steps[0].action_type == RecoveryActionType.RESTART_SERVICE


def test_recovery_api_integration():
    # Because main.py defaults to ai_provider="mock" (via config default),
    # hitting the endpoint should invoke the MockRecoveryPlanner.

    reasoning_payload = {
        "summary": "Mock summary",
        "observed_facts": [],
        "likely_root_causes": ["sim-worker"],
        "propagation_interpretation": "Interp",
        "uncertainty": "Uncertainty",
        "confidence": "HIGH"
    }

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/intelligence/recovery-plan",
            json=reasoning_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "plan_id" in data
        assert len(data["steps"]) == 1
        assert data["steps"][0]["target_component"] == "sim-worker"
        assert data["steps"][0]["action_type"] == "restart_service"
        assert data["is_validated"] is True


def test_schema_prevents_malicious_actions():
    # Pydantic schema intrinsically prevents the LLM from executing commands by strictly typed fields.
    # We test that an action_type not in the Enum is rejected by Pydantic.

    invalid_step = {
        "action_type": "kubectl delete pod",
        "target_component": "database",
        "justification": "Malicious command",
        "estimated_risk": "LOW"
    }

    with pytest.raises(ValueError):
        RecoveryStep(**invalid_step)
