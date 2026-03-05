import pytest

from app.llm.schemas.feedback import FeedbackAnalysis
from app.llm.schemas.parsing import StructuredOutputError, parse_structured_output

_VALID_JSON = """{
    "summary": "User is frustrated with slow load times.",
    "sentiment": "negative",
    "urgency": "high",
    "category": "bug",
    "recommended_action": "Investigate performance regression.",
    "confidence": 0.85,
    "reasoning_short": "Explicit complaint about speed."
}"""


def test_parses_valid_json() -> None:
    analysis = parse_structured_output(_VALID_JSON, FeedbackAnalysis)

    assert analysis.sentiment == "negative"
    assert analysis.category == "bug"


def test_strips_markdown_code_fence() -> None:
    fenced = f"```json\n{_VALID_JSON}\n```"

    analysis = parse_structured_output(fenced, FeedbackAnalysis)

    assert analysis.sentiment == "negative"


def test_raises_on_invalid_json() -> None:
    with pytest.raises(StructuredOutputError):
        parse_structured_output("not json at all", FeedbackAnalysis)


def test_raises_on_schema_mismatch() -> None:
    with pytest.raises(StructuredOutputError):
        parse_structured_output('{"summary": "only a summary"}', FeedbackAnalysis)


def test_error_carries_raw_text_for_repair_prompts() -> None:
    with pytest.raises(StructuredOutputError) as exc_info:
        parse_structured_output("garbage", FeedbackAnalysis)

    assert exc_info.value.raw_text == "garbage"
