from fastapi import Request

from app.llm.providers.registry import ProviderRegistry


def get_provider_registry(request: Request) -> ProviderRegistry:
    registry: ProviderRegistry = request.app.state.provider_registry
    return registry
