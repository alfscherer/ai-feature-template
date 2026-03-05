import json

from app.llm.prompts.loader import load_prompt_template
from app.llm.schemas.feedback import FeedbackAnalysis

# Bumping this is a deliberate act: it changes what the model is asked to do, which means it
# changes behavior in production. See docs/prompt-versioning.md for why this is tracked
# explicitly instead of just editing the prompt file in place.
CURRENT_VERSION = "v1"

_SCHEMA_JSON = json.dumps(FeedbackAnalysis.model_json_schema(), indent=2)


def render_feedback_analysis_prompt(
    *, feedback: str, context: str | None, version: str = CURRENT_VERSION
) -> str:
    template = load_prompt_template("feedback_analysis", version)
    return template.format(
        schema_json=_SCHEMA_JSON,
        feedback=feedback,
        context=context if context else "(none provided)",
    )
