import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """Raised when a provider's response can't be turned into the requested schema."""

    def __init__(self, message: str, *, raw_text: str) -> None:
        super().__init__(message)
        self.raw_text = raw_text


def parse_structured_output(raw_text: str, schema: type[T]) -> T:
    """Parses and validates a model response against `schema`. Never trusts it blindly."""
    cleaned = _strip_code_fence(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(
            f"Response was not valid JSON: {exc}", raw_text=raw_text
        ) from exc

    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise StructuredOutputError(
            f"Response did not match the {schema.__name__} schema: {exc}", raw_text=raw_text
        ) from exc


def _strip_code_fence(text: str) -> str:
    """Models frequently wrap JSON in a ```json ... ``` block despite being told not to."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    without_open = stripped.split("\n", 1)[1] if "\n" in stripped else stripped.removeprefix("```")
    return without_open.removesuffix("```").strip()
