import pytest

from app.core.cache import TTLCache
from app.llm.providers.base import LLMProvider, LLMTextResult, TokenUsage
from app.services.feedback_analysis import (
    CachingFeedbackAnalysisService,
    FeedbackAnalysisOutcome,
    FeedbackAnalysisService,
)

_VALID_RESPONSE = """{
    "summary": "User is frustrated with slow load times.",
    "sentiment": "negative",
    "urgency": "high",
    "category": "bug",
    "recommended_action": "Investigate performance regression.",
    "confidence": 0.85,
    "reasoning_short": "Explicit complaint about speed."
}"""


class _ScriptedProvider(LLMProvider):
    name = "scripted"

    def __init__(self, responses: list[str]) -> None:
        super().__init__()
        self._responses = list(responses)
        self.calls = 0

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        text = self._responses[self.calls]
        self.calls += 1
        return LLMTextResult(
            text=text,
            model=model,
            provider=self.name,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            latency_ms=1.0,
        )


@pytest.mark.asyncio
async def test_analyze_returns_valid_result_on_first_try() -> None:
    provider = _ScriptedProvider([_VALID_RESPONSE])
    service = FeedbackAnalysisService(provider, model="gpt-4o-mini")

    outcome = await service.analyze(feedback="It's slow.", context=None)

    assert outcome.degraded is False
    assert outcome.analysis.category == "bug"
    assert provider.calls == 1
    assert outcome.input_tokens == 100
    assert outcome.output_tokens == 50


@pytest.mark.asyncio
async def test_analyze_repairs_invalid_first_response() -> None:
    provider = _ScriptedProvider(["not valid json", _VALID_RESPONSE])
    service = FeedbackAnalysisService(provider, model="gpt-4o-mini")

    outcome = await service.analyze(feedback="It's slow.", context=None)

    assert outcome.degraded is False
    assert provider.calls == 2
    # Tokens from both the failed attempt and the repair attempt should be counted.
    assert outcome.input_tokens == 200
    assert outcome.output_tokens == 100


@pytest.mark.asyncio
async def test_analyze_returns_degraded_result_when_repair_also_fails() -> None:
    provider = _ScriptedProvider(["not valid json", "still not valid json"])
    service = FeedbackAnalysisService(provider, model="gpt-4o-mini")

    outcome = await service.analyze(feedback="It's slow.", context=None)

    assert outcome.degraded is True
    assert outcome.analysis.confidence == 0.0
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_caching_service_skips_second_identical_call() -> None:
    provider = _ScriptedProvider([_VALID_RESPONSE, _VALID_RESPONSE])
    inner = FeedbackAnalysisService(provider, model="gpt-4o-mini")
    cache: TTLCache[FeedbackAnalysisOutcome] = TTLCache(ttl_seconds=60)
    service = CachingFeedbackAnalysisService(
        inner, cache=cache, provider="scripted", model="gpt-4o-mini"
    )

    first = await service.analyze(feedback="It's slow.", context=None)
    second = await service.analyze(feedback="It's slow.", context=None)

    assert first == second
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_caching_service_treats_different_feedback_as_different_keys() -> None:
    provider = _ScriptedProvider([_VALID_RESPONSE, _VALID_RESPONSE])
    inner = FeedbackAnalysisService(provider, model="gpt-4o-mini")
    cache: TTLCache[FeedbackAnalysisOutcome] = TTLCache(ttl_seconds=60)
    service = CachingFeedbackAnalysisService(
        inner, cache=cache, provider="scripted", model="gpt-4o-mini"
    )

    await service.analyze(feedback="It's slow.", context=None)
    await service.analyze(feedback="It's great!", context=None)

    assert provider.calls == 2
