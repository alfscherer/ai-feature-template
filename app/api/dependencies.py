from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TTLCache
from app.llm.providers.registry import ProviderRegistry
from app.services.feedback_analysis import FeedbackAnalysisOutcome


def get_provider_registry(request: Request) -> ProviderRegistry:
    registry: ProviderRegistry = request.app.state.provider_registry
    return registry


def get_analysis_cache(request: Request) -> TTLCache[FeedbackAnalysisOutcome]:
    cache: TTLCache[FeedbackAnalysisOutcome] = request.app.state.analysis_cache
    return cache


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session
