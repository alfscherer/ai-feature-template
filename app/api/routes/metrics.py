from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas import MetricsResponse
from app.persistence.repository import AnalysisRepository

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_db_session)) -> MetricsResponse:
    snapshot = await AnalysisRepository(db).metrics_snapshot()
    return MetricsResponse(
        total_requests=snapshot.total_requests,
        degraded_requests=snapshot.degraded_requests,
        average_latency_ms=snapshot.average_latency_ms,
        total_input_tokens=snapshot.total_input_tokens,
        total_output_tokens=snapshot.total_output_tokens,
        total_estimated_cost_usd=snapshot.total_estimated_cost_usd,
    )
