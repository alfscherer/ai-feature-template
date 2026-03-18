import time

from anthropic import (
    AnthropicError,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)

from app.llm.providers.base import (
    LLMProvider,
    LLMTextResult,
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    TokenUsage,
)

# Anthropic's API requires an explicit max_tokens; there's no server-side default. This bounds
# our own cost exposure per request as much as it bounds the response length.
_MAX_OUTPUT_TOKENS = 1024


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 30.0,
        client: AsyncAnthropic | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._client = client or AsyncAnthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=0
        )

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        start = time.perf_counter()
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=_MAX_OUTPUT_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except AuthenticationError as exc:
            raise ProviderAuthenticationError(str(exc)) from exc
        except RateLimitError as exc:
            raise ProviderRateLimitError(str(exc)) from exc
        except APITimeoutError as exc:
            raise ProviderTimeoutError(str(exc)) from exc
        except APIConnectionError as exc:
            raise ProviderError(str(exc)) from exc
        except (APIStatusError, AnthropicError) as exc:
            raise ProviderResponseError(str(exc)) from exc

        latency_ms = (time.perf_counter() - start) * 1000

        text = "".join(block.text for block in response.content if block.type == "text")
        if not text:
            raise ProviderResponseError("Anthropic response contained no text content.")

        return LLMTextResult(
            text=text,
            model=response.model,
            provider=self.name,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            latency_ms=latency_ms,
        )
