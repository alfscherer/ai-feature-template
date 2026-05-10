from fastapi import APIRouter

from app.api.routes import analyze, health, metrics, models

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(models.router)
api_router.include_router(analyze.router)
api_router.include_router(metrics.router)
