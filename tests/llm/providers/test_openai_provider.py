from unittest.mock import AsyncMock

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from app.llm.providers.base import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.llm.providers.openai import OpenAIProvider

_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _completion(content: str | None, *, model: str = "gpt-4o-mini") -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-test",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(role="assistant", content=content),
            )
        ],
        created=0,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _make_provider(client: AsyncMock) -> OpenAIProvider:
    return OpenAIProvider(api_key="test-key", client=client)


@pytest.mark.asyncio
async def test_generate_text_returns_result_with_usage_and_latency() -> None:
    client = AsyncMock()
    client.chat.completions.create.return_value = _completion("hello there")
    provider = _make_provider(client)

    result = await provider.generate_text(prompt="hi", model="gpt-4o-mini")

    assert result.text == "hello there"
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_generate_text_raises_on_empty_message_content() -> None:
    client = AsyncMock()
    client.chat.completions.create.return_value = _completion(None)
    provider = _make_provider(client)

    with pytest.raises(ProviderResponseError):
        await provider.generate_text(prompt="hi", model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_generate_text_maps_authentication_error() -> None:
    client = AsyncMock()
    response = httpx.Response(401, request=_REQUEST, json={"error": {"message": "bad key"}})
    client.chat.completions.create.side_effect = AuthenticationError(
        "bad key", response=response, body=None
    )
    provider = _make_provider(client)

    with pytest.raises(ProviderAuthenticationError):
        await provider.generate_text(prompt="hi", model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_generate_text_maps_rate_limit_error() -> None:
    client = AsyncMock()
    response = httpx.Response(429, request=_REQUEST, json={"error": {"message": "slow down"}})
    client.chat.completions.create.side_effect = RateLimitError(
        "slow down", response=response, body=None
    )
    provider = _make_provider(client)

    with pytest.raises(ProviderRateLimitError):
        await provider.generate_text(prompt="hi", model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_generate_text_maps_timeout_error() -> None:
    client = AsyncMock()
    client.chat.completions.create.side_effect = APITimeoutError(_REQUEST)
    provider = _make_provider(client)

    with pytest.raises(ProviderTimeoutError):
        await provider.generate_text(prompt="hi", model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_generate_text_maps_connection_error() -> None:
    client = AsyncMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=_REQUEST)
    provider = _make_provider(client)

    with pytest.raises(ProviderConnectionError):
        await provider.generate_text(prompt="hi", model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_generate_text_maps_generic_status_error() -> None:
    client = AsyncMock()
    response = httpx.Response(500, request=_REQUEST, json={"error": {"message": "oops"}})
    client.chat.completions.create.side_effect = APIStatusError(
        "oops", response=response, body=None
    )
    provider = _make_provider(client)

    with pytest.raises(ProviderResponseError):
        await provider.generate_text(prompt="hi", model="gpt-4o-mini")
