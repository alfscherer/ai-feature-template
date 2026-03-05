# Why prompts are versioned

A prompt is part of the application's behavior, not a comment or a config nicety. Changing the
wording of a prompt can change the distribution of outputs as much as changing the model does --
sometimes more. Treating prompt edits like any other code change (implicit, unversioned,
overwritten in place) makes it impossible to answer basic operational questions:

- Which prompt produced the analysis a customer is disputing?
- Did our classification accuracy regress because of the new model, or the new prompt we
  shipped in the same week?
- Can we roll back the prompt without rolling back the code that calls it?

## How it works here

Prompts live as plain text files under `app/llm/prompts/<task>/<version>.txt`, outside of any
Python logic. Each result produced by the feedback analyzer records the prompt version that
generated it (see `AnalyzeMetadata.prompt_version`), the same way it records the model and
provider.

`CURRENT_VERSION` in `app/llm/prompts/render.py` picks which version is used by default; the
evaluation harness (`evals/`) can run the same dataset against multiple versions side by side
and compare them, which is the only reliable way to tell whether a prompt change is actually
an improvement.

## What this doesn't solve

Versioning a prompt string doesn't version the model, the system's temperature/sampling
settings, or the provider's own model updates -- a "v1" prompt run today against
`gpt-4o-mini` is not guaranteed to behave identically to the same prompt run against it six
months ago. Prompt version is one input to reproducibility, not the whole story.
