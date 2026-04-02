import asyncio
import logging
import random

from app.llm.providers.base import (
    LLMProvider,
    LLMTextResult,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)

# Deliberately an explicit list of leaf types, not the ProviderError base class: every specific
# error type (including the ones we don't want to retry, like authentication and malformed
# responses) inherits from it, so including the base here would retry everything. Retrying a
# bad API key or a request the provider consistently rejects just burns time and tokens without
# changing the outcome; rate limits, timeouts, and connection drops usually do resolve.
_RETRYABLE_EXCEPTIONS = (ProviderRateLimitError, ProviderTimeoutError, ProviderConnectionError)


class RetryPolicy:
    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5,
        max_delay_seconds: float = 8.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds

    def delay_seconds(self, attempt: int) -> float:
        """Full-jitter exponential backoff. `attempt` is the 1-indexed attempt that just failed."""
        capped = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))
        return random.uniform(0, capped)


class RetryingProvider(LLMProvider):
    """Adds bounded retry with exponential backoff to any LLMProvider.

    This is a decorator, not a subclass of the wrapped provider: it applies the same policy
    regardless of which provider is underneath, so retry behavior doesn't have to be
    reimplemented (and potentially get out of sync) in every provider.
    """

    def __init__(self, provider: LLMProvider, *, policy: RetryPolicy | None = None) -> None:
        super().__init__(timeout_seconds=provider.timeout_seconds)
        self._provider = provider
        self.name = provider.name
        self._policy = policy or RetryPolicy()

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        last_error: ProviderError | None = None

        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                return await self._provider.generate_text(prompt=prompt, model=model)
            except _RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                if attempt == self._policy.max_attempts:
                    break
                delay = self._policy.delay_seconds(attempt)
                logger.warning(
                    "provider call failed, retrying",
                    extra={
                        "provider": self._provider.name,
                        "attempt": attempt,
                        "max_attempts": self._policy.max_attempts,
                        "delay_seconds": round(delay, 3),
                        "error": str(exc),
                    },
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error
