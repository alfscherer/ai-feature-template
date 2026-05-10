from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import RequestContextMiddleware
from app.api.router import api_router
from app.core.cache import TTLCache
from app.core.config import get_settings
from app.llm.providers.factory import build_provider_registry
from app.observability.logging import configure_logging
from app.persistence.database import create_all_tables, create_engine, create_session_factory
from app.services.feedback_analysis import FeedbackAnalysisOutcome


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    engine = create_engine(settings.database_url)
    await create_all_tables(engine)
    app.state.session_factory = create_session_factory(engine)

    app.state.provider_registry = build_provider_registry(settings)
    app.state.analysis_cache = TTLCache[FeedbackAnalysisOutcome](
        ttl_seconds=settings.cache_ttl_seconds
    )

    yield

    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AI Feedback Analyzer",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        lifespan=_lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
