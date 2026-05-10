import json
import logging
import sys
from typing import Any

from app.observability.context import request_id_var

# Every attribute a plain LogRecord carries -- computed from a real one rather than hardcoded,
# so it stays correct if the stdlib adds fields in a future Python version. Anything beyond
# this set on a record came from `extra=`, which is exactly what we want to surface.
_BASE_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _BASE_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestIdFilter(logging.Filter):
    """Injects the current request ID into every record that doesn't already carry one.

    Most call sites don't set request_id explicitly -- that's the point of the ContextVar --
    but a caller that does (the request-completion log line needs its value read before the
    ContextVar is reset) should win rather than be silently overwritten with whatever the
    ContextVar holds by the time this filter runs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Structured (JSON-lines) logging to stdout.

    Deliberately does not log request bodies, provider responses, or API keys -- see
    docs/observability.md for what's included and why raw feedback text isn't logged by
    default even though it's stored in the database (different retention and access
    expectations: logs commonly flow to third-party aggregators with broad access; the
    database is the system of record with its own access control).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
