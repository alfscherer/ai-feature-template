from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import AnalysisRecord


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    total_requests: int
    degraded_requests: int
    average_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float | None


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: AnalysisRecord) -> None:
        self._session.add(record)
        await self._session.commit()

    async def get(self, record_id: str) -> AnalysisRecord | None:
        return await self._session.get(AnalysisRecord, record_id)

    async def list_recent(self, limit: int = 50) -> list[AnalysisRecord]:
        result = await self._session.execute(
            select(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(limit)
        )
        return list(result.scalars())

    async def metrics_snapshot(self) -> MetricsSnapshot:
        totals = (
            await self._session.execute(
                select(
                    func.count(AnalysisRecord.id),
                    func.avg(AnalysisRecord.latency_ms),
                    func.sum(AnalysisRecord.input_tokens),
                    func.sum(AnalysisRecord.output_tokens),
                    func.sum(AnalysisRecord.estimated_cost_usd),
                )
            )
        ).one()
        total_requests, avg_latency_ms, total_input_tokens, total_output_tokens, total_cost = totals

        degraded_requests = await self._session.scalar(
            select(func.count())
            .select_from(AnalysisRecord)
            .where(AnalysisRecord.degraded.is_(True))
        )

        return MetricsSnapshot(
            total_requests=total_requests or 0,
            degraded_requests=degraded_requests or 0,
            average_latency_ms=avg_latency_ms or 0.0,
            total_input_tokens=total_input_tokens or 0,
            total_output_tokens=total_output_tokens or 0,
            total_estimated_cost_usd=total_cost,
        )
