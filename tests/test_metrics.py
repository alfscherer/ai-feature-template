from fastapi.testclient import TestClient

from app.api.dependencies import get_provider_registry
from app.llm.providers.base import LLMProvider, LLMTextResult, TokenUsage
from app.llm.providers.registry import ProviderRegistry
from app.main import app

_VALID_RESPONSE = """{
    "summary": "User is happy.",
    "sentiment": "positive",
    "urgency": "low",
    "category": "praise",
    "recommended_action": "No action needed.",
    "confidence": 0.9,
    "reasoning_short": "Positive tone."
}"""


class _FakeProvider(LLMProvider):
    name = "openai"

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        return LLMTextResult(
            text=_VALID_RESPONSE,
            model=model,
            provider=self.name,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            latency_ms=10.0,
        )


def test_metrics_are_zero_with_no_recorded_requests(client: TestClient) -> None:
    response = client.get("/api/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 0
    assert body["degraded_requests"] == 0
    assert body["average_latency_ms"] == 0.0
    assert body["total_estimated_cost_usd"] is None


def test_metrics_reflect_recorded_requests(client: TestClient) -> None:
    registry = ProviderRegistry()
    registry.register(_FakeProvider())
    app.dependency_overrides[get_provider_registry] = lambda: registry

    client.post("/api/analyze", json={"feedback": "Great job!"})
    client.post("/api/analyze", json={"feedback": "Also great!"})

    response = client.get("/api/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 2
    assert body["degraded_requests"] == 0
    assert body["total_input_tokens"] == 200
    assert body["total_output_tokens"] == 100
