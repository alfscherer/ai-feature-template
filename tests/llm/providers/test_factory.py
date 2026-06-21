import pytest

from app.core.config import Settings
from app.llm.providers.factory import build_provider, build_provider_registry
from app.llm.providers.retry import RetryingProvider


def test_build_provider_raises_for_missing_api_key() -> None:
    settings = Settings(openai_api_key=None, anthropic_api_key=None)

    with pytest.raises(ValueError, match="openai"):
        build_provider("openai", settings)


def test_build_provider_raises_for_unknown_name() -> None:
    settings = Settings()

    with pytest.raises(ValueError, match="mistral"):
        build_provider("mistral", settings)


def test_build_provider_wraps_with_retry() -> None:
    settings = Settings(openai_api_key="test-key")

    provider = build_provider("openai", settings)

    assert isinstance(provider, RetryingProvider)
    assert provider.name == "openai"


def test_build_provider_builds_anthropic_too() -> None:
    settings = Settings(anthropic_api_key="test-key")

    provider = build_provider("anthropic", settings)

    assert isinstance(provider, RetryingProvider)
    assert provider.name == "anthropic"


def test_build_provider_registry_only_includes_configured_providers() -> None:
    settings = Settings(openai_api_key="test-key", anthropic_api_key=None)

    registry = build_provider_registry(settings)

    assert registry.names() == ["openai"]


def test_build_provider_registry_includes_both_when_both_configured() -> None:
    settings = Settings(openai_api_key="test-key", anthropic_api_key="test-key")

    registry = build_provider_registry(settings)

    assert set(registry.names()) == {"openai", "anthropic"}
