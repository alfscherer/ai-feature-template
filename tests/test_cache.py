import time

from app.core.cache import TTLCache


def test_returns_none_for_missing_key() -> None:
    cache: TTLCache[str] = TTLCache(ttl_seconds=60)

    assert cache.get("missing") is None


def test_returns_stored_value_before_expiry() -> None:
    cache: TTLCache[str] = TTLCache(ttl_seconds=60)

    cache.set("key", "value")

    assert cache.get("key") == "value"
    assert len(cache) == 1


def test_expired_entry_is_evicted_on_read() -> None:
    cache: TTLCache[str] = TTLCache(ttl_seconds=0.01)

    cache.set("key", "value")
    time.sleep(0.02)

    assert cache.get("key") is None
    assert len(cache) == 0
