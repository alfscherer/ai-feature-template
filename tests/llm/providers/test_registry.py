import pytest

from app.llm.providers.base import LLMProvider, LLMTextResult, TokenUsage
from app.llm.providers.registry import ProviderRegistry


class _FakeProvider(LLMProvider):
    name = "fake"

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        return LLMTextResult(
            text="ok",
            model=model,
            provider=self.name,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            latency_ms=0.0,
        )


def test_register_and_get_round_trips() -> None:
    registry = ProviderRegistry()
    provider = _FakeProvider()

    registry.register(provider)

    assert registry.get("fake") is provider
    assert registry.names() == ["fake"]


def test_get_unknown_provider_raises() -> None:
    registry = ProviderRegistry()

    with pytest.raises(ValueError, match="fake"):
        registry.get("fake")
