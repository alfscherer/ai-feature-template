from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.persistence.models import Base


def create_engine(database_url: str) -> AsyncEngine:
    if database_url.startswith("sqlite"):
        _ensure_sqlite_directory_exists(database_url)
    return create_async_engine(database_url)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_all_tables(engine: AsyncEngine) -> None:
    """Fine for a demo project. A real deployment would use a migration tool (Alembic) instead
    of letting the app derive its own schema at startup -- see DECISIONS.md.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def _ensure_sqlite_directory_exists(database_url: str) -> None:
    # sqlite+aiosqlite:///./data/feedback.db -> ./data/feedback.db
    path_part = database_url.split("///", 1)[-1]
    if path_part in (":memory:", ""):
        return
    Path(path_part).parent.mkdir(parents=True, exist_ok=True)
