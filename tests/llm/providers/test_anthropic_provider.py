from unittest.mock import AsyncMock

import httpx
import pytest
from anthropic import AuthenticationError, RateLimitError
from anthropic.types import Message, TextBlock, Usage

from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.base import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
)

_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _message(text: str | None, *, model: str = "claude-3-5-haiku-20241022") -> Message:
    content = [TextBlock(type="text", text=text)] if text else []
    return Message(
        id="msg-test",
        content=content,
        model=model,
        role="assistant",
        stop_reason="end_turn",
        stop_sequence=None,
        type="message",
        usage=Usage(input_tokens=20, output_tokens=8),
    )


def _make_provider(client: AsyncMock) -> AnthropicProvider:
    return AnthropicProvider(api_key="test-key", client=client)


@pytest.mark.asyncio
async def test_generate_text_returns_result_with_usage_and_latency() -> None:
    client = AsyncMock()
    client.messages.create.return_value = _message("hello there")
    provider = _make_provider(client)

    result = await provider.generate_text(prompt="hi", model="claude-3-5-haiku-20241022")

    assert result.text == "hello there"
    assert result.provider == "anthropic"
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 8
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_generate_text_raises_on_empty_content() -> None:
    client = AsyncMock()
    client.messages.create.return_value = _message(None)
    provider = _make_provider(client)

    with pytest.raises(ProviderResponseError):
        await provider.generate_text(prompt="hi", model="claude-3-5-haiku-20241022")


@pytest.mark.asyncio
async def test_generate_text_maps_authentication_error() -> None:
    client = AsyncMock()
    response = httpx.Response(401, request=_REQUEST, json={"error": {"message": "bad key"}})
    client.messages.create.side_effect = AuthenticationError(
        "bad key", response=response, body=None
    )
    provider = _make_provider(client)

    with pytest.raises(ProviderAuthenticationError):
        await provider.generate_text(prompt="hi", model="claude-3-5-haiku-20241022")


@pytest.mark.asyncio
async def test_generate_text_maps_rate_limit_error() -> None:
    client = AsyncMock()
    response = httpx.Response(429, request=_REQUEST, json={"error": {"message": "slow down"}})
    client.messages.create.side_effect = RateLimitError("slow down", response=response, body=None)
    provider = _make_provider(client)

    with pytest.raises(ProviderRateLimitError):
        await provider.generate_text(prompt="hi", model="claude-3-5-haiku-20241022")
