from fastapi.testclient import TestClient

from app.api.dependencies import get_provider_registry
from app.llm.providers.base import LLMProvider, LLMTextResult, ProviderError, TokenUsage
from app.llm.providers.registry import ProviderRegistry
from app.main import app

_VALID_RESPONSE = """{
    "summary": "User is happy with the new dashboard.",
    "sentiment": "positive",
    "urgency": "low",
    "category": "praise",
    "recommended_action": "No action needed.",
    "confidence": 0.92,
    "reasoning_short": "Clearly positive, no complaints raised."
}"""


class _FakeProvider(LLMProvider):
    name = "openai"

    def __init__(self, *, text: str | None = None, error: Exception | None = None) -> None:
        super().__init__()
        self._text = text
        self._error = error

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        if self._error is not None:
            raise self._error
        assert self._text is not None
        return LLMTextResult(
            text=self._text,
            model=model,
            provider=self.name,
            usage=TokenUsage(input_tokens=120, output_tokens=60),
            latency_ms=1.0,
        )


def _override_registry(provider: LLMProvider) -> None:
    registry = ProviderRegistry()
    registry.register(provider)
    app.dependency_overrides[get_provider_registry] = lambda: registry


def test_analyze_rejects_empty_feedback(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"feedback": ""})

    assert response.status_code == 422


def test_analyze_rejects_oversized_feedback(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"feedback": "x" * 5000})

    assert response.status_code == 422


def test_analyze_returns_503_when_no_provider_configured(client: TestClient) -> None:
    app.dependency_overrides[get_provider_registry] = ProviderRegistry

    response = client.post("/api/analyze", json={"feedback": "The export button is broken."})

    assert response.status_code == 503


def test_analyze_returns_structured_result(client: TestClient) -> None:
    _override_registry(_FakeProvider(text=_VALID_RESPONSE))

    response = client.post("/api/analyze", json={"feedback": "I love the new dashboard!"})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["sentiment"] == "positive"
    assert body["analysis"]["category"] == "praise"
    assert body["metadata"]["provider"] == "openai"
    assert body["metadata"]["prompt_version"] == "v1"
    assert body["metadata"]["degraded"] is False


def test_analyze_maps_provider_error_to_502(client: TestClient) -> None:
    _override_registry(_FakeProvider(error=ProviderError("upstream is down")))

    response = client.post("/api/analyze", json={"feedback": "The export button is broken."})

    assert response.status_code == 502
