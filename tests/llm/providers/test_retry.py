import pytest

from app.llm.providers.base import (
    LLMProvider,
    LLMTextResult,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    TokenUsage,
)
from app.llm.providers.retry import RetryingProvider, RetryPolicy


class _FlakyProvider(LLMProvider):
    name = "flaky"

    def __init__(self, exceptions_then_success: list[Exception | None]) -> None:
        super().__init__()
        self._script = list(exceptions_then_success)
        self.calls = 0

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        outcome = self._script[self.calls]
        self.calls += 1
        if outcome is not None:
            raise outcome
        return LLMTextResult(
            text="ok",
            model=model,
            provider=self.name,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            latency_ms=0.0,
        )


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.llm.providers.retry.asyncio.sleep", _instant_sleep)


@pytest.mark.asyncio
async def test_succeeds_after_transient_failure() -> None:
    inner = _FlakyProvider([ProviderRateLimitError("slow down"), None])
    provider = RetryingProvider(inner, policy=RetryPolicy(max_attempts=3))

    result = await provider.generate_text(prompt="hi", model="m")

    assert result.text == "ok"
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_gives_up_after_max_attempts() -> None:
    inner = _FlakyProvider(
        [ProviderRateLimitError("a"), ProviderRateLimitError("b"), ProviderRateLimitError("c")]
    )
    provider = RetryingProvider(inner, policy=RetryPolicy(max_attempts=3))

    with pytest.raises(ProviderRateLimitError):
        await provider.generate_text(prompt="hi", model="m")

    assert inner.calls == 3


@pytest.mark.asyncio
async def test_retries_connection_errors() -> None:
    inner = _FlakyProvider([ProviderConnectionError("dns failure"), None])
    provider = RetryingProvider(inner, policy=RetryPolicy(max_attempts=3))

    result = await provider.generate_text(prompt="hi", model="m")

    assert result.text == "ok"
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_does_not_retry_authentication_errors() -> None:
    inner = _FlakyProvider([ProviderAuthenticationError("bad key"), None])
    provider = RetryingProvider(inner, policy=RetryPolicy(max_attempts=3))

    with pytest.raises(ProviderAuthenticationError):
        await provider.generate_text(prompt="hi", model="m")

    assert inner.calls == 1


@pytest.mark.asyncio
async def test_does_not_retry_response_errors() -> None:
    inner = _FlakyProvider([ProviderResponseError("garbage"), None])
    provider = RetryingProvider(inner, policy=RetryPolicy(max_attempts=3))

    with pytest.raises(ProviderResponseError):
        await provider.generate_text(prompt="hi", model="m")

    assert inner.calls == 1


def test_delay_seconds_is_bounded_and_grows() -> None:
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=10.0)

    for attempt, cap in [(1, 1.0), (2, 2.0), (3, 4.0), (10, 10.0)]:
        delay = policy.delay_seconds(attempt)
        assert 0 <= delay <= cap
