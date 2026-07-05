# Architecture decisions

Each entry: context, the decision, alternatives considered, consequences (including the ones
that cut against the decision). These aren't presented as permanently correct -- they're
correct for this feature's current shape and volume, and each entry says what would make it
wrong.

## 1. Raw provider SDKs behind a thin internal abstraction, not a framework

**Context:** the feature needs to call at least two LLM providers (OpenAI, Anthropic) through
one consistent interface, with retries, timeouts, and cost tracking applied uniformly.

**Decision:** use each provider's official SDK directly, wrapped in a small internal interface
(`LLMProvider`, one abstract method) owned by this codebase.

**Alternatives considered:**
- *LangChain (or a similar framework)* would provide a provider abstraction, prompt templates,
  and output parsers out of the box. Rejected for this feature: the abstraction this feature
  needs is one method wide (`generate_text()`) and about 40 lines per provider to implement --
  a framework's abstraction is built for a much larger surface (chains, agents, retrievers) that
  this feature doesn't use, and adopting it means depending on its versioning cadence and
  learning its abstractions to debug anything that goes wrong inside them.
- *A hand-rolled HTTP client per provider (no SDK)* would remove the SDK dependency entirely.
  Rejected: the official SDKs already handle request signing, retries-we-don't-want (disabled
  via `max_retries=0`), streaming primitives we might want later, and type-safe request/response
  models. Reimplementing that has a real cost with no corresponding benefit here.

**Consequences:** adding a third provider costs one new file implementing `LLMProvider` plus a
factory entry -- no framework upgrade risk, no abstraction to learn beyond this repo's own 40
lines. The cost is on the other side: this codebase owns retry/backoff, cost-table maintenance,
and error-mapping that a framework might have provided for more providers out of the box. That
trade is worth it while there are two providers and one interface method; it would be worth
revisiting with five+ providers or a need for framework-provided features (agents, complex
chains) this feature doesn't currently have.

## 2. Structured outputs are required

**Context:** the feature's output feeds downstream systems (or a human reviewer) that need
`sentiment`, `urgency`, `category`, etc. as typed values, not prose to be re-parsed later.

**Decision:** every model response is parsed and validated against a Pydantic schema
(`FeedbackAnalysis`) before it leaves the service layer. A response that doesn't validate gets
one repair attempt, then a labeled degraded fallback. Nothing downstream ever sees an
unvalidated response.

**Alternatives considered:**
- *Trust the model's output directly* (assume well-formed JSON, `json.loads()` and go). Rejected:
  models do not reliably produce well-formed output matching an exact schema, especially under
  prompt variation or adversarial input, and a downstream consumer expecting `urgency: "high"`
  should not receive `urgency: "pretty urgent I'd say"`.
- *Use a provider's native structured-output / function-calling mode as the only validation.*
  These help (they reduce how often validation fails) but are provider-specific and not a
  substitute for validating on receipt -- a provider's guarantee about its own output format is
  not a guarantee your application's schema hasn't drifted from what you're asking for.

**Consequences:** every response costs a validation pass and, on failure, a second LLM call
(the repair attempt) -- extra latency and cost on the unhappy path. In exchange, nothing that
consumes `FeedbackAnalysis` needs defensive parsing of its own, and a schema violation is
visible and logged (`degraded: true`) instead of silently propagating malformed data.

## 3. Prompt versions are explicit

**Context:** a prompt's wording is part of the application's behavior; changing it can shift
output distribution as much as changing the model does.

**Decision:** prompts live as versioned files (`app/llm/prompts/feedback_analysis/v1.txt`,
`v2.txt`, ...), and every result records which version produced it
(`AnalyzeMetadata.prompt_version`).

**Alternatives considered:**
- *Edit the prompt string in place, rely on git history for versioning.* Rejected: git history
  tells you when a prompt changed, not which version generated a specific stored result, and it
  gives you no way to run two versions side by side without checking out two branches.
- *Store prompts in the database, editable at runtime.* Would allow non-deploy prompt changes
  (useful for some products) at the cost of making prompt changes invisible to code review and
  to `make eval`. Rejected here since the priority is evaluability, not runtime flexibility.

**Consequences:** every prompt change is a file, reviewable and diffable. The evaluation harness
can compare versions directly. The cost: one more piece of state to keep in sync (the "current"
version pointer in `render.py`), and prompt files that aren't run through an LLM linter or
type-checker of any kind -- their correctness is only checked by `make eval` and actual usage.

## 4. Evaluation is part of the repository, not an afterthought

**Context:** the actual hard part of shipping an LLM feature responsibly is knowing whether a
change (prompt, model, provider) made things better or worse, not making a demo call succeed
once.

**Decision:** `evals/` ships in the same repository, runs against the same service code the API
uses, and is one of the required deliverables of this project, not a follow-up task.

**Alternatives considered:**
- *Ship the feature, add evaluation later once there's a problem.* This is how most naive LLM
  integrations are actually built, and it's precisely the failure mode this repository exists to
  demonstrate an alternative to: without an evaluation harness in place *before* a prompt or
  model change ships, "it seems better" is the only available signal, and it's an unreliable one.
- *A separate, ad hoc evaluation notebook outside the repository.* Rejected because it would rot
  independently of the application code (no CI awareness of drift, easy to forget it exists) and
  couldn't reuse `FeedbackAnalysisService` without duplicating it.

**Consequences:** the repository carries a synthetic dataset and a runner that costs real API
calls to execute, which is unusual overhead for a demo project to commit to maintaining -- and
that's the point being demonstrated, not an accident.

## 5. SQLite is acceptable here, not necessarily in production

**Context:** the feature needs to persist an audit trail of analyses (for `GET /api/metrics` and
general debuggability) with minimal operational overhead for local development and this
portfolio's demo scope.

**Decision:** SQLite via SQLAlchemy's async engine (`aiosqlite`), with the schema and repository
written so a swap to PostgreSQL is a `DATABASE_URL` change.

**Alternatives considered:**
- *PostgreSQL from the start*, via docker-compose. Would be more "production-representative" but
  adds a service a reviewer has to run to try this repository at all, for a demo whose request
  volume and concurrency needs don't require it.
- *No persistence at all* (metadata only in the API response). Rejected: it would remove the
  ability to demonstrate `GET /api/metrics` or any audit trail, both called out as required
  concerns.

**Consequences:** local development and this demo need nothing beyond a Python environment.
The cost is real and specific: SQLite's single-writer behavior is not something to rely on under
real concurrent write load, and `metadata.create_all()` at startup (used here) is not a
migration strategy — see "What I would change at production scale" in the README. Swapping the
`DATABASE_URL` to PostgreSQL gets you a compatible schema; it does not get you migrations,
connection pooling tuned for production load, or a backup strategy, and none of those are in
scope here.

## 6. Raw prompts/responses are not logged by default

**Context:** structured logging (request ID, provider, model, latency, tokens, cost) is required
for debugging and observability. It's tempting to also log the feedback text and the model's raw
response, since that's often the most useful thing when debugging a bad result.

**Decision:** feedback text, context, and model responses are never included in log output at
any level by default. They are persisted to the application database instead, which a developer
can query by the same request ID that appears in logs.

**Alternatives considered:**
- *Log everything at DEBUG level, keep INFO clean.* Rejected as the default: a developer running
  locally with `LOG_LEVEL=DEBUG` for an unrelated reason would still be logging customer text.
  Making the safe behavior the default (with any future debug-logging opt-in requiring a
  deliberate, separate flag) is more robust than relying on people to always pick the safe log
  level.
- *Log a redacted/truncated version.* Deferred, not adopted: redaction is easy to get wrong
  (worth doing carefully if a real deployment needs it) and truncation still leaks the start of
  potentially sensitive text.

**Consequences:** debugging a specific bad result requires looking it up in the database by
request ID rather than reading it straight out of the log stream -- one extra step, in exchange
for logs that are safe to ship to a third-party aggregator with broader access and different
retention than the application's own database.

## 7. When fine-tuning would and would not make sense

**Context:** fine-tuning wasn't used anywhere in this repository, worth stating explicitly why.

**Decision:** this feature relies entirely on prompting general-purpose models, not fine-tuning.

**When it wouldn't make sense (this feature, as built):** the feedback-analysis task is exactly
the kind of thing general-purpose instruction-tuned models are already good at (classification
against a schema, from natural-language input, with no house style or proprietary format to
learn). Fine-tuning needs a labeled dataset an order of magnitude larger than this repository's
26-example evaluation set, a retraining pipeline to maintain as requirements drift, and it
trades prompt-level flexibility (change the instructions, redeploy in seconds) for a slower
iteration loop (retrain, re-evaluate, redeploy a new model version). None of that cost is
justified for a task prompting already handles well.

**When it would:** fine-tuning earns its cost when (a) there's a large, high-quality labeled
dataset that reflects a specific house style, taxonomy, or domain vocabulary that prompting
struggles to reproduce consistently; (b) latency or cost at high volume make a smaller
fine-tuned model preferable to a larger general-purpose one prompted into the same behavior; or
(c) the task needs a capability (a very specific output format, a narrow domain) where
few-shot prompting demonstrably plateaus below the accuracy bar. None of those conditions hold
for this feature today; a real deployment with the evaluation harness in place would have actual
data to decide if that ever changes -- which is the point of having the harness.
