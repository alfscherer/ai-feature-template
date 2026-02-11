from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Feedback Analyzer",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
