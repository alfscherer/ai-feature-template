from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """Base class for all provider-level failures."""


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    """The provider returned something we couldn't make sense of."""


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class LLMTextResult:
    text: str
    model: str
    provider: str
    usage: TokenUsage
    latency_ms: float


class LLMProvider(ABC):
    """A thin, provider-agnostic interface over a chat-completion style LLM API.

    A provider's only job is turning a prompt into text and reporting honestly how long
    that took and how many tokens it used. Retries, schema validation, prompt construction,
    and caching live above this layer so they apply the same way regardless of which
    provider answered the request.
    """

    name: str

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult: ...
