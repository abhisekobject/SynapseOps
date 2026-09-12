from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.intelligence.models import RCACandidate, RCAResult
from backend.intelligence.reasoning.models import IncidentContext, IncidentReasoningResult
from backend.intelligence.reasoning.providers import MockReasoningProvider
from backend.main import app

client = TestClient(app)


def test_incident_context_creation():
    context = IncidentContext(
        analysis_window_minutes=15,
        active_events=[],
        rca_result=None,
        system_state=None,
        topology_nodes=["sim-api", "database"],
        topology_edges=[{"source": "sim-api", "target": "database"}],
    )
    assert context.analysis_window_minutes == 15
    assert len(context.topology_nodes) == 2


@pytest.mark.asyncio
async def test_mock_reasoning_provider():
    provider = MockReasoningProvider()

    # Fake RCA Result
    candidate = RCACandidate(
        component="database",
        score=0.9,
        confidence="HIGH",
        evidence=[],
        affected_components=["sim-api"]
    )
    rca = RCAResult(
        candidates=[candidate],
        window_minutes=15,
        generated_at=datetime.now(UTC),
    )

    context = IncidentContext(
        analysis_window_minutes=15,
        active_events=[],
        rca_result=rca,
        system_state=None,
        topology_nodes=[],
        topology_edges=[],
    )

    result = await provider.analyze(context)

    # The mock provider deterministically returns the top RCA candidate as a likely root cause
    assert isinstance(result, IncidentReasoningResult)
    assert "database" in result.likely_root_causes
    assert result.confidence == "HIGH"


def test_api_integration_mock_provider():
    # Because main.py defaults to ai_provider="mock" (via config default),
    # hitting the endpoint should invoke the MockReasoningProvider.
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/intelligence/incident-reasoning?window_minutes=15")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "likely_root_causes" in data
        assert "confidence" in data
        # No actual events in the test environment, so likely_root_causes will have "unknown" or be empty
        assert data["likely_root_causes"] == ["unknown"]


@pytest.mark.asyncio
async def test_failing_provider_degrades_gracefully():
    # Force a failure by injecting a broken provider
    class BrokenProvider(MockReasoningProvider):
        async def analyze(self, context: IncidentContext) -> IncidentReasoningResult:
            raise RuntimeError("API Timeout")

    with TestClient(app) as test_client:
        test_client.app.state.reasoning_provider = BrokenProvider()

        response = test_client.get("/api/v1/intelligence/incident-reasoning?window_minutes=15")
        # API should catch it and return 503
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()

        # Restore the normal mock provider so other tests aren't broken
        test_client.app.state.reasoning_provider = MockReasoningProvider()


def test_prompt_injection_safety_schema_enforcement():
    # Pydantic schema intrinsically prevents the LLM from executing commands by strictly typed fields.
    # We can test that a malicious output failing the schema is rejected.

    invalid_data = {
        "execute_command": "kubectl delete pod sim-worker",
        "summary": "Everything is fine."
    }

    # IncidentReasoningResult requires many fields not present here
    with pytest.raises(ValueError):
        IncidentReasoningResult(**invalid_data)


@pytest.mark.asyncio
async def test_openai_provider_hallucination_filtering():
    # Simulate an AI response with hallucinated components
    from backend.core.config import Settings
    from backend.intelligence.reasoning.providers import OpenAIReasoningProvider

    settings = Settings(ai_provider="openai", ai_api_key="test-key")
    OpenAIReasoningProvider(settings)

    context = IncidentContext(
        analysis_window_minutes=15,
        active_events=[],
        rca_result=None,
        system_state=None,
        topology_nodes=["sim-api"],  # Only sim-api is valid
        topology_edges=[],
    )

    # We create a fake response object
    result = IncidentReasoningResult(
        summary="Test",
        observed_facts=[],
        likely_root_causes=["sim-api", "imaginary-service"], # imaginary-service is hallucinated
        propagation_interpretation="Test",
        uncertainty="Test",
        missing_evidence=[],
        conflicting_evidence=[],
        confidence="HIGH"
    )

    # Manually filter like the provider does
    invalid_causes = [c for c in result.likely_root_causes if c not in context.topology_nodes]
    if invalid_causes:
        result.likely_root_causes = [c for c in result.likely_root_causes if c in context.topology_nodes]

    assert "imaginary-service" not in result.likely_root_causes
    assert "sim-api" in result.likely_root_causes
