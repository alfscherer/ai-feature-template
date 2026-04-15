from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.cache import TTLCache
from app.core.config import Settings, get_settings
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.base import LLMProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.registry import ProviderRegistry
from app.llm.providers.retry import RetryingProvider, RetryPolicy
from app.persistence.database import create_all_tables, create_engine, create_session_factory
from app.services.feedback_analysis import FeedbackAnalysisOutcome


def _build_provider_registry(settings: Settings) -> ProviderRegistry:
    registry = ProviderRegistry()
    policy = RetryPolicy(max_attempts=settings.llm_max_attempts)

    def register(provider: LLMProvider) -> None:
        registry.register(RetryingProvider(provider, policy=policy))

    if settings.openai_api_key:
        register(
            OpenAIProvider(
                api_key=settings.openai_api_key,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        )
    if settings.anthropic_api_key:
        register(
            AnthropicProvider(
                api_key=settings.anthropic_api_key,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        )
    return registry


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    engine = create_engine(settings.database_url)
    await create_all_tables(engine)
    app.state.session_factory = create_session_factory(engine)

    app.state.provider_registry = _build_provider_registry(settings)
    app.state.analysis_cache = TTLCache[FeedbackAnalysisOutcome](
        ttl_seconds=settings.cache_ttl_seconds
    )

    yield

    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Feedback Analyzer",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        lifespan=_lifespan,
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
