"""Runs the evaluation dataset against one or two (provider, model, prompt_version) configs.

Usage:
    python -m evals.run
    python -m evals.run --provider openai --model gpt-4o-mini --prompt-version v1
    python -m evals.run --compare-prompt-version v2
    python -m evals.run --compare-provider anthropic --compare-model claude-3-5-haiku-20241022

Requires a real API key for whichever provider(s) you run against -- this hits live LLM APIs
and will incur real cost. See docs/evaluation.md for what these numbers do and don't tell you.
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.llm.providers.base import ProviderError
from app.llm.providers.factory import build_provider
from app.llm.schemas.feedback import FeedbackCategory, Sentiment, Urgency
from app.services.feedback_analysis import FeedbackAnalysisService
from evals.dataset import EvalExample, load_dataset
from evals.metrics import ExampleResult, Summary, summarize


@dataclass(frozen=True, slots=True)
class RunConfig:
    provider: str
    model: str
    prompt_version: str

    @property
    def label(self) -> str:
        return f"{self.provider}/{self.model}@{self.prompt_version}"


async def run_config(config: RunConfig, examples: list[EvalExample], settings: Settings) -> Summary:
    provider = build_provider(config.provider, settings)
    service = FeedbackAnalysisService(
        provider, model=config.model, prompt_version=config.prompt_version
    )

    results = [await _run_example(service, example) for example in examples]
    return summarize(config.label, results)


async def _run_example(service: FeedbackAnalysisService, example: EvalExample) -> ExampleResult:
    try:
        outcome = await service.analyze(feedback=example.feedback, context=example.context)
    except ProviderError as exc:
        return ExampleResult(
            example_id=example.id,
            tags=example.tags,
            schema_valid=False,
            sentiment_match=None,
            category_match=None,
            urgency_match=None,
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=None,
            error=str(exc),
        )

    return ExampleResult(
        example_id=example.id,
        tags=example.tags,
        schema_valid=not outcome.degraded,
        sentiment_match=_match(example.expected_sentiment, outcome.analysis.sentiment),
        category_match=_match(example.expected_category, outcome.analysis.category),
        urgency_match=_match(example.expected_urgency, outcome.analysis.urgency),
        latency_ms=outcome.latency_ms,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        estimated_cost_usd=outcome.estimated_cost_usd,
    )


def _match(
    expected: Sentiment | FeedbackCategory | Urgency | None,
    actual: Sentiment | FeedbackCategory | Urgency,
) -> bool | None:
    if expected is None:
        return None
    return expected == actual


def print_summary_table(summaries: list[Summary]) -> None:
    headers = [
        "config",
        "n",
        "errors",
        "schema valid",
        "sentiment",
        "category",
        "urgency",
        "avg latency",
        "tokens in/out",
        "est. cost",
    ]
    rows = [
        [
            s.label,
            str(s.example_count),
            str(s.error_count),
            f"{s.schema_validity_rate:.0%}",
            _fmt_rate(s.sentiment_agreement),
            _fmt_rate(s.category_agreement),
            _fmt_rate(s.urgency_agreement),
            f"{s.mean_latency_ms:.0f}ms",
            f"{s.total_input_tokens}/{s.total_output_tokens}",
            (
                f"${s.total_estimated_cost_usd:.4f}"
                if s.total_estimated_cost_usd is not None
                else "n/a"
            ),
        ]
        for s in summaries
    ]

    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(" | ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)))


def _fmt_rate(rate: float | None) -> str:
    return f"{rate:.0%}" if rate is not None else "n/a"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt-version", default=None)
    parser.add_argument("--compare-provider", default=None)
    parser.add_argument("--compare-model", default=None)
    parser.add_argument("--compare-prompt-version", default=None)
    return parser.parse_args(argv)


async def _main(argv: list[str]) -> int:
    args = _parse_args(argv)
    settings = get_settings()
    examples = load_dataset()

    base = RunConfig(
        provider=args.provider or settings.default_provider,
        model=args.model or settings.default_model,
        prompt_version=args.prompt_version or "v1",
    )
    configs = [base]

    if args.compare_provider or args.compare_model or args.compare_prompt_version:
        configs.append(
            RunConfig(
                provider=args.compare_provider or base.provider,
                model=args.compare_model or base.model,
                prompt_version=args.compare_prompt_version or base.prompt_version,
            )
        )

    try:
        summaries = [await run_config(config, examples, settings) for config in configs]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Ran {len(examples)} examples from evals/dataset.jsonl\n")
    print_summary_table(summaries)
    print(
        "\nSchema validity and label agreement are the easy parts to measure. They are not the "
        "same as 'the analysis is good' -- see docs/evaluation.md for what this table doesn't "
        "tell you, and read the security-sensitive examples' output by hand at least once."
    )
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main(sys.argv[1:])))


if __name__ == "__main__":
    main()
