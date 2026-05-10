import json
import logging

from app.observability.context import request_id_var
from app.observability.logging import JSONFormatter, RequestIdFilter


def _make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="something happened",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_includes_standard_fields() -> None:
    record = _make_record()

    payload = json.loads(JSONFormatter().format(record))

    assert payload["message"] == "something happened"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert "timestamp" in payload


def test_formatter_includes_extra_fields() -> None:
    record = _make_record(provider="openai", latency_ms=42.0)

    payload = json.loads(JSONFormatter().format(record))

    assert payload["provider"] == "openai"
    assert payload["latency_ms"] == 42.0


def test_formatter_omits_message_duplicate_of_msg() -> None:
    record = _make_record()

    payload = json.loads(JSONFormatter().format(record))

    # `message` should appear exactly once, not once from getMessage() and once as a raw attr.
    assert list(json.loads(JSONFormatter().format(record)).keys()).count("message") == 1
    assert payload["message"] == "something happened"


def test_request_id_filter_reads_contextvar() -> None:
    token = request_id_var.set("req-123")
    try:
        record = _make_record()
        RequestIdFilter().filter(record)
        assert record.request_id == "req-123"  # type: ignore[attr-defined]
    finally:
        request_id_var.reset(token)


def test_request_id_filter_defaults_to_none_outside_a_request() -> None:
    record = _make_record()

    RequestIdFilter().filter(record)

    assert record.request_id is None  # type: ignore[attr-defined]
