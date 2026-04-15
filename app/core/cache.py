import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """An in-process cache with a fixed time-to-live per entry.

    This is intentionally the simplest thing that works: a single dict, guarded by nothing,
    living in one process's memory. It's correct for local development and a single-replica
    deployment. It is NOT correct for multiple replicas (each would have its own, inconsistent
    cache) and doesn't survive a restart. See docs/caching.md for the Redis swap-in.
    """

    def __init__(self, *, ttl_seconds: float = 3600.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl_seconds)

    def __len__(self) -> int:
        return len(self._store)
