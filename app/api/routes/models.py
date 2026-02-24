from typing import Final

from fastapi import APIRouter

from app.api.schemas import ModelInfo
from app.core.config import get_settings

router = APIRouter(tags=["models"])

# The models each provider is known to support. This will move to a registry query once
# providers can report their own supported models; for now it's a small static catalog.
_KNOWN_MODELS: Final[list[tuple[str, str]]] = [
    ("openai", "gpt-4o-mini"),
]


@router.get("/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    settings = get_settings()
    return [
        ModelInfo(
            provider=provider,
            model=model,
            is_default=(provider == settings.default_provider and model == settings.default_model),
        )
        for provider, model in _KNOWN_MODELS
    ]
