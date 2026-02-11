from typing import Final

from fastapi import APIRouter

from app.api.schemas import ModelInfo

router = APIRouter(tags=["models"])

# Static for now. Once the provider abstraction lands, this will be replaced by a registry
# that reports the models each configured provider actually supports.
_AVAILABLE_MODELS: Final[list[ModelInfo]] = [
    ModelInfo(provider="openai", model="gpt-4o-mini", is_default=True),
    ModelInfo(provider="anthropic", model="claude-3-5-haiku-20241022", is_default=False),
]


@router.get("/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    return _AVAILABLE_MODELS
