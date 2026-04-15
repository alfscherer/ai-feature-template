from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.persistence.database import create_all_tables
from app.persistence.models import AnalysisRecord
from app.persistence.repository import AnalysisRepository


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await create_all_tables(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session
    await engine.dispose()


def _record(record_id: str = "rec-1") -> AnalysisRecord:
    return AnalysisRecord(
        id=record_id,
        feedback="The export button is broken.",
        context=None,
        provider="openai",
        model="gpt-4o-mini",
        prompt_version="v1",
        sentiment="negative",
        urgency="high",
        category="bug",
        confidence=0.9,
        latency_ms=120.0,
        input_tokens=100,
        output_tokens=40,
        estimated_cost_usd=0.0001,
        degraded=False,
    )


@pytest.mark.asyncio
async def test_save_and_get_round_trip(session: AsyncSession) -> None:
    repository = AnalysisRepository(session)

    await repository.save(_record())
    fetched = await repository.get("rec-1")

    assert fetched is not None
    assert fetched.feedback == "The export button is broken."
    assert fetched.category == "bug"


@pytest.mark.asyncio
async def test_get_missing_record_returns_none(session: AsyncSession) -> None:
    repository = AnalysisRepository(session)

    assert await repository.get("does-not-exist") is None


@pytest.mark.asyncio
async def test_list_recent_orders_newest_first(session: AsyncSession) -> None:
    repository = AnalysisRepository(session)
    await repository.save(_record("rec-1"))
    await repository.save(_record("rec-2"))

    recent = await repository.list_recent(limit=10)

    assert [r.id for r in recent] == ["rec-2", "rec-1"]
