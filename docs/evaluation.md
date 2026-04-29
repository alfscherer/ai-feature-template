# Evaluation

`make eval` runs `evals/dataset.jsonl` (26 synthetic examples) through the real analysis
pipeline -- the same `FeedbackAnalysisService` the API uses, not a separate code path -- and
reports schema validity, label agreement, latency, token usage, and estimated cost.

This requires a real provider API key and makes real LLM calls. It is not run in CI for that
reason (no key, and it costs money and takes time); it's a tool for a developer to run
before changing a prompt or switching a default model, not a gate every commit has to pass.

## Comparing two configurations

```bash
python -m evals.run --provider openai --model gpt-4o-mini --prompt-version v1
python -m evals.run --compare-prompt-version v2
python -m evals.run --compare-provider anthropic --compare-model claude-3-5-haiku-20241022
```

The second form runs both configs against the identical dataset and prints one table with a row
per config, so a prompt or model change can be judged against the same inputs rather than
against a vague sense of "it seems better."

## The dataset

26 examples across positive, negative, ambiguous, sarcastic, very short, very long,
multilingual, contradictory, security-sensitive, and malformed feedback, plus a few
miscellaneous edge cases (shouting, emoji-only, a bare URL, a technical bug report with a stack
trace). It's synthetic -- written for this repository, not sampled from any real product or
real users.

Roughly a third of the examples have no expected sentiment/category/urgency label at all
(`expected_sentiment: null`, etc. in the dataset). That's deliberate: for genuinely ambiguous,
sarcastic, or contradictory feedback, there often isn't one correct label, and scoring the model
against a label we made up ourselves would just measure agreement with our own guess. Those
examples are still checked for schema validity -- did the model produce a well-formed
`FeedbackAnalysis` at all -- which is a real, objective thing to measure even when the "right"
classification isn't.

## What the summary table tells you, and what it doesn't

It tells you: did the output parse and validate, does the classification match a label a human
would probably agree with for the clear-cut cases, how long did it take, and roughly what it
cost.

It does not tell you: whether the `summary` is well-written, whether `recommended_action` is
actually a good recommendation, or whether `reasoning_short` reflects real reasoning rather than
a plausible-sounding justification for whatever label came out. Those are judgment calls a
human has to make by reading actual outputs -- there's no metric in this table that substitutes
for that. The `security-2` example (an embedded prompt-injection attempt) is specifically there
to be read by hand: the aggregate table will show it as schema-valid and possibly
label-correct even if the model's `summary` or `recommended_action` field got hijacked into
echoing the injected text, because nothing in the schema forbids that. Structured output
validation bounds *how* a compromised response can misbehave (it must still be a
`FeedbackAnalysis`), not *whether* the content of any given field was influenced by the attempt.

## A model, a snapshot in time

LLM providers update models under a fixed name (a "gpt-4o-mini" today is not contractually the
same weights as six months ago), and API responses are not deterministic even at temperature 0
across all providers. A single `make eval` run is a snapshot, not a permanent characterization
of a model's behavior. Treat a result as "this is what we measured on this date against this
dataset," not as a lasting certification.
