from app.core.config import Settings
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.base import LLMProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.registry import ProviderRegistry
from app.llm.providers.retry import RetryingProvider, RetryPolicy

# Kept in one place so the API app and the evaluation harness (evals/run.py) construct
# providers identically -- same retry policy, same timeout, same API key source.
_PROVIDER_NAMES = ("openai", "anthropic")


def _build_unwrapped(name: str, settings: Settings) -> LLMProvider | None:
    if name == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAIProvider(
            api_key=settings.openai_api_key, timeout_seconds=settings.llm_timeout_seconds
        )
    if name == "anthropic":
        if not settings.anthropic_api_key:
            return None
        return AnthropicProvider(
            api_key=settings.anthropic_api_key, timeout_seconds=settings.llm_timeout_seconds
        )
    raise ValueError(f"Unknown provider: {name!r}")


def build_provider(name: str, settings: Settings) -> LLMProvider:
    provider = _build_unwrapped(name, settings)
    if provider is None:
        raise ValueError(f"No API key configured for provider {name!r}.")

    return RetryingProvider(provider, policy=RetryPolicy(max_attempts=settings.llm_max_attempts))


def build_provider_registry(settings: Settings) -> ProviderRegistry:
    registry = ProviderRegistry()
    for name in _PROVIDER_NAMES:
        try:
            registry.register(build_provider(name, settings))
        except ValueError:
            continue
    return registry
