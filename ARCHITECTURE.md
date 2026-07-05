# Architecture

This document explains how the pieces fit together and, more importantly, the tradeoffs behind
each boundary. None of this is "the one correct way" to build an LLM-backed feature -- it's one
coherent set of choices for this feature's shape (single request in, single structured result
out, no streaming, moderate volume). A chat product, a batch pipeline, or a
thousands-of-requests-per-second service would reasonably draw several of these lines
differently.

## Layers

```
app/
  api/          HTTP boundary: routes, request/response schemas, middleware, dependency wiring
  services/     Orchestration: what to do when a step fails, what gets persisted/cached
  llm/          Everything about talking to a model: providers, prompts, schemas, retries
  persistence/  SQLAlchemy models and a thin repository
  core/         Cross-cutting: config, the cache primitive
  observability/  Structured logging, request-ID propagation
```

### API layer (`app/api/`)

Owns HTTP concerns only: request validation (via Pydantic models with explicit length limits),
status code mapping, and wiring dependencies together for a route. `app/api/routes/analyze.py`
is the one route with real logic in it, and that logic is orchestration -- look up a provider,
wrap the service with caching, call it, map exceptions to status codes, persist the result --
not business logic. It deliberately does not use a `Depends()` factory for provider lookup; see
[DECISIONS.md](DECISIONS.md) and the commit that fixed this for why a dependency that can raise
is the wrong place to put a check that should happen after body validation.

### Service layer (`app/services/feedback_analysis.py`)

`FeedbackAnalysisService` owns the one policy decision in this codebase that isn't purely
mechanical: what to do when a model's output doesn't validate. It renders a versioned prompt,
calls a provider, and on a schema failure gets exactly one repair attempt before returning a
clearly-marked degraded result. It never raises a schema error to its caller and never returns
unvalidated data — see [DECISIONS.md](DECISIONS.md) for why that boundary exists.

`CachingFeedbackAnalysisService` wraps it with the same interface (a `Protocol`, not a base
class -- there's nothing to share except the method signature) to add caching without the
service needing to know caching exists.

### LLM layer (`app/llm/`)

- **`providers/base.py`**: `LLMProvider` is one abstract method, `generate_text()`. Everything a
  provider is expected to report -- text, token usage, latency, which provider answered -- is in
  the return type, not scattered across side effects.
- **`providers/openai.py`, `providers/anthropic.py`**: each provider's whole job is mapping its
  SDK's calling convention and its SDK's exceptions onto `LLMProvider`'s interface and the
  shared `ProviderError` hierarchy. Nothing above this layer imports `openai` or `anthropic`.
- **`providers/retry.py`**: `RetryingProvider` decorates any `LLMProvider` with bounded
  exponential backoff for the specific errors worth retrying (rate limits, timeouts, connection
  failures) and none of the ones that aren't (bad auth, malformed responses). It's a decorator
  specifically so retry policy is defined once and applies identically regardless of which
  provider is active -- see the commit that added it for a real bug this structure caught.
- **`prompts/`**: plain text files, not Python. `render.py` fills in the JSON schema and inputs;
  `loader.py` just reads a file by name and version. See
  [docs/prompt-versioning.md](docs/prompt-versioning.md).
- **`schemas/`**: `feedback.py` defines the contract (`FeedbackAnalysis`); `parsing.py` is the
  only place that turns a raw string into a validated instance of it, with one job -- parse,
  validate, raise a typed error with enough context to build a repair prompt from.

### Persistence (`app/persistence/`)

SQLAlchemy 2.0 async, one table (`AnalysisRecord`), one thin repository. See
[DECISIONS.md](DECISIONS.md) for why SQLite now and what changes for PostgreSQL (short version:
the `DATABASE_URL`, and eventually a migration tool -- not this schema or the repository's
interface).

### Observability (`app/observability/`) and caching (`app/core/cache.py`)

Covered in depth in [docs/observability.md](docs/observability.md) and
[docs/caching.md](docs/caching.md) respectively. The short version of both: a request ID
propagated via `contextvars` ties logs together without threading it through every function
signature, and a single-process `TTLCache` is honestly labeled as single-process rather than
pretending to be a distributed cache it isn't.

## Provider abstraction: what it buys, what it costs

**Buys:** business logic (the service layer, the API layer) never branches on which provider is
active. Adding a third provider means implementing `LLMProvider` and registering it in
`app/llm/providers/factory.py` -- nothing else changes. Testing the service layer means mocking
one small interface instead of two different SDKs' worth of surface area.

**Costs:** the abstraction is intentionally thin (`generate_text()` plus reported usage/latency),
which means it doesn't try to normalize every provider-specific capability (function calling
conventions, provider-specific structured-output modes, prompt caching features some providers
expose natively). If a future requirement needs one of those, it either goes through the shared
interface awkwardly or the interface grows a provider-specific escape hatch -- both are real
costs of choosing a small interface over a maximal one. The bet made here is that "swap models
freely, validate everything ourselves" is worth more than "use every provider-specific feature
optimally," for this feature. That bet could reasonably go the other way for a feature that
leans harder on one provider's specific capabilities.

## Evaluation architecture

`evals/run.py` builds a real `FeedbackAnalysisService` from the same provider/prompt-rendering
code the API uses -- not a parallel path -- and runs it against `evals/dataset.jsonl`. This means
an evaluation result is a claim about the code that actually serves requests, at the cost of the
evaluation script needing real API keys and costing real money to run (which is also why it
isn't part of CI; see [docs/evaluation.md](docs/evaluation.md)).

The alternative -- a lighter, mocked "evaluation" that doesn't hit a real model -- would be free
and fast, but it would only tell you the harness's plumbing works, not whether a prompt or model
choice is actually good. Both kinds of test exist here: the mocked ones (`tests/`) check the
plumbing; `evals/` checks the plumbing *and* the actual model behavior, at the cost of needing a
human to run it deliberately rather than on every push.

## Failure handling

The reliability table in the README maps failure modes to behavior. Architecturally, the
handling is layered on purpose:

1. **Request validation** (Pydantic, `app/api/schemas.py`) rejects malformed/oversized input
   before any LLM call, cheaply.
2. **Provider-level errors** (`ProviderError` and subclasses) are raised by the provider,
   optionally retried by `RetryingProvider`, and if they still fail, mapped to an HTTP status by
   the route -- `500` for our own misconfiguration (bad key), `502` for everything else upstream,
   `503` if no provider is configured at all.
3. **Schema-level errors** (`StructuredOutputError`) never reach the API layer as errors --
   `FeedbackAnalysisService` absorbs them into the repair-then-degrade policy and always returns
   a valid `FeedbackAnalysisOutcome`.

Two real bugs were caught building this, both instructive about why layering and tests matter
here specifically:

- A retryable-exception check that included the shared `ProviderError` base class, which meant
  every subclass matched it -- including the ones explicitly meant not to be retried
  (authentication, malformed response). Caught by a test asserting a non-retryable error wasn't
  retried; fixed by retrying an explicit list of leaf types instead of the base class.
- A `Depends()`-based provider lookup that could raise before FastAPI finished validating the
  request body, turning a `422` into a misleading `503`. Fixed by moving the check into the
  route handler, after the body is already validated.

Both are the kind of bug that's easy to introduce in a system with several layers of error
handling and easy to miss without deliberately testing the *boundary* between layers, not just
each layer in isolation.

## Caching

Covered fully in [docs/caching.md](docs/caching.md). Architecturally, it sits as a decorator
around the service layer (not inside the provider, not inside the route), so it applies to any
`FeedbackAnalyzer`-shaped thing regardless of what's underneath it, and can be removed by
deleting one line in the route without touching anything else.

## A note on what this document isn't

This isn't a claim that every boundary here is load-bearing at every scale. The provider
abstraction, the repair-then-degrade policy, and the caching decorator all pay for themselves at
this feature's current shape and volume. At meaningfully larger scale, some of these would
change -- see the README's "What I would change at production scale" -- and at smaller scope
(a single-provider prototype with no evaluation needs) several of these layers would be
overhead rather than value. Match the architecture to the problem in front of you, not to this
document.
