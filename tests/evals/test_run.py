import pytest

from app.llm.providers.base import LLMProvider, LLMTextResult, ProviderError, TokenUsage
from app.llm.schemas.feedback import Sentiment
from app.services.feedback_analysis import FeedbackAnalysisService
from evals.dataset import EvalExample
from evals.metrics import ExampleResult, summarize
from evals.run import RunConfig, _match, _run_example, print_summary_table

_VALID_RESPONSE = """{
    "summary": "User is happy with the new dashboard.",
    "sentiment": "positive",
    "urgency": "low",
    "category": "praise",
    "recommended_action": "No action needed.",
    "confidence": 0.9,
    "reasoning_short": "Clearly positive tone."
}"""


class _FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, *, text: str | None = None, error: Exception | None = None) -> None:
        super().__init__()
        self._text = text
        self._error = error

    async def generate_text(self, *, prompt: str, model: str) -> LLMTextResult:
        if self._error is not None:
            raise self._error
        assert self._text is not None
        return LLMTextResult(
            text=self._text,
            model=model,
            provider=self.name,
            usage=TokenUsage(input_tokens=10, output_tokens=5),
            latency_ms=1.0,
        )


def test_run_config_label_is_human_readable() -> None:
    config = RunConfig(provider="openai", model="gpt-4o-mini", prompt_version="v1")

    assert config.label == "openai/gpt-4o-mini@v1"


def test_match_returns_none_when_no_expected_label() -> None:
    assert _match(None, Sentiment.POSITIVE) is None


def test_match_compares_expected_to_actual() -> None:
    assert _match(Sentiment.POSITIVE, Sentiment.POSITIVE) is True
    assert _match(Sentiment.POSITIVE, Sentiment.NEGATIVE) is False


@pytest.mark.asyncio
async def test_run_example_scores_a_successful_analysis() -> None:
    service = FeedbackAnalysisService(_FakeProvider(text=_VALID_RESPONSE), model="gpt-4o-mini")
    example = EvalExample(
        id="ex-1",
        feedback="Love it!",
        expected_sentiment=Sentiment.POSITIVE,
        tags=["positive"],
    )

    result = await _run_example(service, example)

    assert result.example_id == "ex-1"
    assert result.schema_valid is True
    assert result.sentiment_match is True
    assert result.error is None


@pytest.mark.asyncio
async def test_run_example_records_provider_errors_without_raising() -> None:
    service = FeedbackAnalysisService(
        _FakeProvider(error=ProviderError("upstream is down")), model="gpt-4o-mini"
    )
    example = EvalExample(id="ex-1", feedback="Love it!")

    result = await _run_example(service, example)

    assert result.error == "upstream is down"
    assert result.schema_valid is False


def test_print_summary_table_does_not_raise(capsys: pytest.CaptureFixture[str]) -> None:
    summary = summarize(
        "cfg",
        [
            ExampleResult(
                example_id="ex-1",
                tags=[],
                schema_valid=True,
                sentiment_match=True,
                category_match=None,
                urgency_match=None,
                latency_ms=42.0,
                input_tokens=10,
                output_tokens=5,
                estimated_cost_usd=0.001,
            )
        ],
    )

    print_summary_table([summary])

    captured = capsys.readouterr()
    assert "cfg" in captured.out
