from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import AnalysisRecord


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
