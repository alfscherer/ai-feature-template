from contextvars import ContextVar

# Set once per request by RequestContextMiddleware, read by the logging filter so every log
# line emitted while handling a request carries its request_id without threading it through
# every function signature in between.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
