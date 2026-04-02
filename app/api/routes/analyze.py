import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_provider_registry
from app.api.schemas import AnalyzeMetadata, AnalyzeRequest, AnalyzeResponse
from app.core.config import get_settings
from app.llm.providers.base import ProviderAuthenticationError, ProviderError
from app.llm.providers.registry import ProviderRegistry
from app.services.feedback_analysis import FeedbackAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_feedback(
    payload: AnalyzeRequest,
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> AnalyzeResponse:
    # Provider lookup happens here, after `payload` is already validated, rather than in a
    # Depends() factory: a dependency that raises runs during FastAPI's dependency-solving
    # step, which can preempt body validation and turn a 422 into a misleading 503.
    settings = get_settings()
    try:
        provider = registry.get(settings.default_provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No LLM provider is configured. Set a provider API key in the environment.",
        ) from exc

    service = FeedbackAnalysisService(provider, model=settings.default_model)

    try:
        outcome = await service.analyze(feedback=payload.feedback, context=payload.context)
    except ProviderAuthenticationError as exc:
        # This is our misconfiguration, not the caller's or the provider's -- a 502 would
        # wrongly suggest retrying against a different provider might help.
        logger.error(
            "provider authentication failed", extra={"provider": settings.default_provider}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM provider authentication failed.",
        ) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AnalyzeResponse(
        analysis=outcome.analysis,
        metadata=AnalyzeMetadata(
            request_id=str(uuid4()),
            provider=outcome.provider,
            model=outcome.model,
            prompt_version=outcome.prompt_version,
            latency_ms=outcome.latency_ms,
            input_tokens=outcome.input_tokens,
            output_tokens=outcome.output_tokens,
            estimated_cost_usd=outcome.estimated_cost_usd,
            degraded=outcome.degraded,
        ),
    )
