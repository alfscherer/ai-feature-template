from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExampleResult:
    example_id: str
    tags: list[str]
    schema_valid: bool  # False only if even the repair attempt failed (a degraded result)
    sentiment_match: bool | None  # None = no ground truth to compare against
    category_match: bool | None
    urgency_match: bool | None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    error: str | None = None  # set if the provider call itself failed


@dataclass(frozen=True, slots=True)
class Summary:
    label: str
    example_count: int
    error_count: int
    schema_validity_rate: float
    sentiment_agreement: float | None
    category_agreement: float | None
    urgency_agreement: float | None
    mean_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float | None


def summarize(label: str, results: list[ExampleResult]) -> Summary:
    if not results:
        raise ValueError("Cannot summarize an empty result set.")

    scored = [r for r in results if r.error is None]

    return Summary(
        label=label,
        example_count=len(results),
        error_count=len(results) - len(scored),
        schema_validity_rate=_rate(r.schema_valid for r in scored),
        sentiment_agreement=_agreement_rate(r.sentiment_match for r in scored),
        category_agreement=_agreement_rate(r.category_match for r in scored),
        urgency_agreement=_agreement_rate(r.urgency_match for r in scored),
        mean_latency_ms=_mean(r.latency_ms for r in scored),
        total_input_tokens=sum(r.input_tokens for r in scored),
        total_output_tokens=sum(r.output_tokens for r in scored),
        total_estimated_cost_usd=_sum_optional(r.estimated_cost_usd for r in scored),
    )


def _rate(values: Iterable[bool]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(1 for v in values if v) / len(values)


def _agreement_rate(values: Iterable[bool | None]) -> float | None:
    graded = [v for v in values if v is not None]
    if not graded:
        return None
    return sum(1 for v in graded if v) / len(graded)


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)


def _sum_optional(values: Iterable[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present)
