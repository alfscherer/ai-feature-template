from pydantic import BaseModel, Field

from app.llm.schemas.feedback import FeedbackAnalysis

MAX_FEEDBACK_LENGTH = 4000
MAX_CONTEXT_LENGTH = 1000


class AnalyzeRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=MAX_FEEDBACK_LENGTH)
    context: str | None = Field(default=None, max_length=MAX_CONTEXT_LENGTH)


class AnalyzeMetadata(BaseModel):
    request_id: str
    provider: str
    model: str
    prompt_version: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    degraded: bool = False


class AnalyzeResponse(BaseModel):
    analysis: FeedbackAnalysis
    metadata: AnalyzeMetadata


class ModelInfo(BaseModel):
    provider: str
    model: str
    is_default: bool = False


class HealthResponse(BaseModel):
    status: str


class MetricsResponse(BaseModel):
    total_requests: int
    degraded_requests: int
    average_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float | None
