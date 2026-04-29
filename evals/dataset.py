import json
from pathlib import Path

from pydantic import BaseModel

from app.llm.schemas.feedback import FeedbackCategory, Sentiment, Urgency

DEFAULT_DATASET_PATH = Path(__file__).parent / "dataset.jsonl"


class EvalExample(BaseModel):
    id: str
    feedback: str
    context: str | None = None

    # None means "no confident ground truth" -- e.g. sarcasm or genuinely ambiguous feedback --
    # and the example is excluded from agreement scoring for that field rather than penalizing
    # the model for not guessing the same way we did.
    expected_sentiment: Sentiment | None = None
    expected_category: FeedbackCategory | None = None
    expected_urgency: Urgency | None = None

    tags: list[str] = []
    notes: str | None = None


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> list[EvalExample]:
    examples = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(EvalExample.model_validate(json.loads(line)))
    return examples
