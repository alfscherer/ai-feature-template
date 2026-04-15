from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Each test gets its own SQLite file so tests can't see each other's persisted rows, and
    # the lifespan (which creates the engine and tables) needs to see the override before it
    # runs -- hence clearing the cached Settings rather than just setting the env var.
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    get_settings.cache_clear()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()
