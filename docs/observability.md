# Observability

## What's logged

Every request gets a request ID -- reused from an inbound `X-Request-ID` header if the caller
sends one, generated otherwise -- set in a `contextvars.ContextVar` for the duration of the
request (`app/observability/context.py`) and injected into every log line by a logging filter,
without threading it through every function signature between the API route and the LLM
provider call.

Logs are JSON lines on stdout (`app/observability/logging.py`). Two log lines matter most:

- `request completed` (one per HTTP request): method, path, status code, duration, request ID.
- `feedback analysis completed` (one per `/api/analyze` call that reaches a provider): provider,
  model, prompt version, latency, input/output tokens, estimated cost, and whether the result
  was degraded.

Retry attempts (`app/llm/providers/retry.py`) log a warning per retry with the attempt number,
so the retry count for a request is reconstructable from the logs even though it isn't a field
on any single record.

## What's deliberately not logged

Feedback text, context, and the model's response are never logged, by default, at any log
level. This is a default worth being explicit about, not an oversight:

- Feedback often contains whatever a customer decided to type, which can include things they
  didn't mean to share broadly (account details, other people's names, pasted error output with
  internal URLs).
- Logs commonly flow to a different system than the application database -- a third-party log
  aggregator, a broader-access dashboard, longer or different retention -- so the "logs are
  fine, the DB isn't" framing runs backwards more often than not.
- Debugging a bad result rarely needs the raw text in the log line anyway: the request ID
  correlates the log entry to the full `AnalysisRecord` in the database, which does store the
  feedback, for whoever has DB access to look it up. See DECISIONS.md for why raw content isn't
  logged by default, and how to opt into it deliberately (e.g. a redacted debug mode) if a real
  deployment needs it.

No API keys are logged either -- they never enter a log call in the first place; they only ever
flow into the provider SDK client constructors.

## Cost and latency in three places

Estimated cost per request shows up in: the API response (`AnalyzeMetadata.estimated_cost_usd`),
the `feedback analysis completed` log line, and `GET /api/metrics` (aggregated across all
persisted requests). The evaluation harness (`evals/run.py`) reports the same figure aggregated
per eval run. All four read from the same `estimate_cost_usd()` pricing table
(`app/llm/providers/pricing.py`), so there's one place to update prices, not four.

## Connecting this to a real observability stack

None of this is wired to an external system, on purpose -- adding one would mean picking a
vendor for a portfolio project. The seams are where you'd expect:

- **Log shipping**: JSON lines on stdout are what most log collectors (Vector, Fluent Bit, the
  CloudWatch/Datadog/Grafana Loki agents) expect by default. Point one at the process's stdout
  and the `request_id` field becomes the correlation key across log lines and across services.
- **Metrics**: `GET /api/metrics` is a starting point, not a real metrics pipeline -- it's a
  point-in-time SQL aggregate, not a time series. A real deployment would emit counters/
  histograms (e.g. via `prometheus_client` or an OpenTelemetry metrics exporter) at the same
  points this code already logs from, and scrape them instead of polling this endpoint.
- **Tracing**: the request ID plays the role a trace ID would. Swapping in real distributed
  tracing (OpenTelemetry) would replace the custom `ContextVar` with its context propagation
  and turn the two log lines above into spans, but the instrumentation points -- request
  boundary, provider call boundary -- don't move.
- **Alerting**: `degraded` and provider error rates (502/500/503 responses) are the two signals
  worth paging on. Both are already visible in the structured logs; a real deployment would
  alert on their rate over a window rather than on any single occurrence.
