import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
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


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 30.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        # max_retries=0: retry policy is owned by the layer above the provider, so a
        # provider's failure modes are visible to it instead of being silently absorbed.
        self._client = client or AsyncOpenAI(
            api_key=api_key, timeout=timeout_seconds, max_retries=0
        )

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        start = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                model=model,
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
        except APIStatusError as exc:
            raise ProviderResponseError(str(exc)) from exc

        latency_ms = (time.perf_counter() - start) * 1000

        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message.content is None:
            raise ProviderResponseError("OpenAI response contained no message content.")

        usage = response.usage
        return LLMTextResult(
            text=choice.message.content,
            model=response.model,
            provider=self.name,
            usage=TokenUsage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
            latency_ms=latency_ms,
        )
