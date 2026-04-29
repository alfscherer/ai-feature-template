import pytest

from evals.metrics import ExampleResult, summarize


def _result(**overrides: object) -> ExampleResult:
    defaults: dict[str, object] = {
        "example_id": "ex-1",
        "tags": [],
        "schema_valid": True,
        "sentiment_match": True,
        "category_match": True,
        "urgency_match": True,
        "latency_ms": 100.0,
        "input_tokens": 10,
        "output_tokens": 5,
        "estimated_cost_usd": 0.001,
        "error": None,
    }
    defaults.update(overrides)
    return ExampleResult(**defaults)  # type: ignore[arg-type]


def test_summarize_empty_raises() -> None:
    with pytest.raises(ValueError):
        summarize("label", [])


def test_summarize_all_correct() -> None:
    results = [_result(example_id="a"), _result(example_id="b")]

    summary = summarize("cfg", results)

    assert summary.example_count == 2
    assert summary.error_count == 0
    assert summary.schema_validity_rate == 1.0
    assert summary.sentiment_agreement == 1.0
    assert summary.mean_latency_ms == 100.0
    assert summary.total_input_tokens == 20
    assert summary.total_estimated_cost_usd == pytest.approx(0.002)


def test_summarize_excludes_ungraded_examples_from_agreement() -> None:
    results = [
        _result(example_id="a", sentiment_match=True),
        _result(example_id="b", sentiment_match=None),
    ]

    summary = summarize("cfg", results)

    # Only one of the two examples has ground truth; agreement is computed over just that one.
    assert summary.sentiment_agreement == 1.0


def test_summarize_reports_no_agreement_when_nothing_is_graded() -> None:
    results = [_result(sentiment_match=None, category_match=None, urgency_match=None)]

    summary = summarize("cfg", results)

    assert summary.sentiment_agreement is None
    assert summary.category_agreement is None
    assert summary.urgency_agreement is None


def test_summarize_counts_errors_separately_from_scored_results() -> None:
    results = [
        _result(example_id="a"),
        _result(example_id="b", error="provider timed out", schema_valid=False),
    ]

    summary = summarize("cfg", results)

    assert summary.example_count == 2
    assert summary.error_count == 1
    # Only the non-error example contributes to the rate.
    assert summary.schema_validity_rate == 1.0
