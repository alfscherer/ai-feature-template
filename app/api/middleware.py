import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.context import request_id_var

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "x-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID (or reuses an inbound one) and logs one line per request.

    The ID goes in a ContextVar so every log line emitted while handling the request --
    including the ones deep in FeedbackAnalysisService -- can be correlated after the fact,
    and it's echoed back as a response header so a caller can report it when something breaks.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers[REQUEST_ID_HEADER] = request_id
            # Logged while the ContextVar is still set, before the `finally` resets it below,
            # so RequestIdFilter picks up the real value instead of the "outside any request"
            # default -- the same mechanism every other log line in the request relies on.
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return response
        finally:
            request_id_var.reset(token)
