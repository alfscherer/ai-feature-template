import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Protocol

from app.core.cache import TTLCache
from app.llm.prompts.render import CURRENT_VERSION, render_feedback_analysis_prompt
from app.llm.providers.base import LLMProvider
from app.llm.providers.pricing import estimate_cost_usd
from app.llm.schemas.feedback import FeedbackAnalysis, FeedbackCategory, Sentiment, Urgency
from app.llm.schemas.parsing import StructuredOutputError, parse_structured_output

logger = logging.getLogger(__name__)

_DEGRADED_ANALYSIS = FeedbackAnalysis(
    summary="Automated analysis could not be completed for this feedback.",
    sentiment=Sentiment.NEUTRAL,
    urgency=Urgency.MEDIUM,
    category=FeedbackCategory.OTHER,
    recommended_action="Route to a human reviewer.",
    confidence=0.0,
    reasoning_short="Response did not match the expected schema, even after a repair attempt.",
)


@dataclass(frozen=True, slots=True)
class FeedbackAnalysisOutcome:
    analysis: FeedbackAnalysis
    provider: str
    model: str
    prompt_version: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    degraded: bool


class FeedbackAnalysisService:
    """Turns free-form feedback into a validated FeedbackAnalysis.

    Owns the one policy decision that matters here: what to do when the model's output
    doesn't validate. It gets one repair attempt (re-prompted with the validation error) before
    falling back to a clearly-marked degraded result. It never raises a schema error up to the
    caller and never returns unvalidated data.
    """

    def __init__(self, provider: LLMProvider, *, model: str) -> None:
        self._provider = provider
        self._model = model

    async def analyze(self, *, feedback: str, context: str | None) -> FeedbackAnalysisOutcome:
        prompt = render_feedback_analysis_prompt(feedback=feedback, context=context)
        start = time.perf_counter()
        input_tokens = 0
        output_tokens = 0

        result = await self._provider.generate_text(prompt=prompt, model=self._model)
        input_tokens += result.usage.input_tokens
        output_tokens += result.usage.output_tokens

        try:
            analysis = parse_structured_output(result.text, FeedbackAnalysis)
            degraded = False
        except StructuredOutputError as error:
            logger.warning(
                "structured output failed validation, attempting repair",
                extra={"provider": self._provider.name, "model": self._model},
            )
            repair_result = await self._provider.generate_text(
                prompt=_build_repair_prompt(prompt, error), model=self._model
            )
            input_tokens += repair_result.usage.input_tokens
            output_tokens += repair_result.usage.output_tokens

            try:
                analysis = parse_structured_output(repair_result.text, FeedbackAnalysis)
                degraded = False
            except StructuredOutputError:
                logger.error(
                    "structured output repair attempt also failed",
                    extra={"provider": self._provider.name, "model": self._model},
                )
                analysis = _DEGRADED_ANALYSIS
                degraded = True

        latency_ms = (time.perf_counter() - start) * 1000
        estimated_cost_usd = estimate_cost_usd(
            self._model, input_tokens=input_tokens, output_tokens=output_tokens
        )

        return FeedbackAnalysisOutcome(
            analysis=analysis,
            provider=self._provider.name,
            model=self._model,
            prompt_version=CURRENT_VERSION,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            degraded=degraded,
        )


class FeedbackAnalyzer(Protocol):
    async def analyze(self, *, feedback: str, context: str | None) -> FeedbackAnalysisOutcome: ...


class CachingFeedbackAnalysisService:
    """Skips the LLM call entirely for feedback this exact provider/model has already analyzed.

    Wraps any FeedbackAnalyzer rather than being built into FeedbackAnalysisService itself, so
    caching can be turned off (or swapped for a different cache) without touching the analysis
    logic. See docs/caching.md for the tradeoffs of the cache implementation.
    """

    def __init__(
        self,
        inner: FeedbackAnalyzer,
        *,
        cache: TTLCache[FeedbackAnalysisOutcome],
        provider: str,
        model: str,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._provider = provider
        self._model = model

    async def analyze(self, *, feedback: str, context: str | None) -> FeedbackAnalysisOutcome:
        key = self._cache_key(feedback=feedback, context=context)

        cached = self._cache.get(key)
        if cached is not None:
            return cached

        outcome = await self._inner.analyze(feedback=feedback, context=context)
        self._cache.set(key, outcome)
        return outcome

    def _cache_key(self, *, feedback: str, context: str | None) -> str:
        digest_input = "\x1f".join(
            [self._provider, self._model, CURRENT_VERSION, feedback, context or ""]
        )
        return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


def _build_repair_prompt(original_prompt: str, error: StructuredOutputError) -> str:
    return (
        f"{original_prompt}\n\n"
        "Your previous response did not match the required schema.\n\n"
        f"Previous response:\n{error.raw_text}\n\n"
        f"Validation error:\n{error}\n\n"
        "Return ONLY a corrected JSON object that matches the schema. No explanation, no "
        "markdown formatting."
    )
