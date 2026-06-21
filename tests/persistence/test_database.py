from pathlib import Path

import pytest

from app.persistence.database import _ensure_sqlite_directory_exists, create_engine


def test_ensure_sqlite_directory_exists_creates_missing_parent(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "feedback.db"
    url = f"sqlite+aiosqlite:///{db_path}"

    _ensure_sqlite_directory_exists(url)

    assert db_path.parent.is_dir()


def test_ensure_sqlite_directory_exists_skips_in_memory_database() -> None:
    _ensure_sqlite_directory_exists("sqlite+aiosqlite:///:memory:")  # must not raise


@pytest.mark.asyncio
async def test_create_engine_creates_directory_for_sqlite_url(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "feedback.db"
    url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_engine(url)
    try:
        assert db_path.parent.is_dir()
    finally:
        await engine.dispose()
