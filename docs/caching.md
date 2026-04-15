# Caching

Identical feedback (same text, context, provider, and model) produces the same request to the
LLM. Caching the result avoids paying for and waiting on that call twice -- this also happens to
be the cheapest way to handle a client retrying the same request after a slow response, one of
the "repeated request" cases called out in the reliability requirements.

## What's here

`app.core.cache.TTLCache` is a single in-process dict with per-entry expiry. It lives on
`app.state` and is shared by all requests handled by that process.

The cache key is a hash of `(provider, model, prompt_version, feedback, context)`. Changing the
prompt version invalidates the cache for that content automatically, which is what you want --
a new prompt version is a new question being asked of the model, not the same one.

## Why not Redis from the start

A single-process, in-memory cache is enough to demonstrate the pattern and to be genuinely
useful for local development, and it adds zero operational surface (no extra service to run,
configure, or monitor). It does not work correctly once there's more than one process or
machine serving traffic: each replica would have its own cache, so a request could hit a warm
cache on one replica and a cold one on another, and nothing is evicted consistently across them.

## What changes with Redis

- Replace `TTLCache` with a thin wrapper around `redis.asyncio.Redis` exposing the same
  `get`/`set` shape, so callers (the analysis service) don't change.
- Use `SETEX` for the TTL instead of tracking expiry in Python.
- Serialize `FeedbackAnalysisOutcome` (it's a plain dataclass of primitives) to JSON going in,
  and validate it back into shape coming out -- don't trust a cache value any more than a fresh
  one, since another version of this service could have written it.
- Nothing above the cache interface -- the service, the API route -- needs to know this
  happened.
