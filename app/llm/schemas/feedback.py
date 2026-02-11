from enum import StrEnum

from pydantic import BaseModel, Field


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackCategory(StrEnum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    PRAISE = "praise"
    COMPLAINT = "complaint"
    QUESTION = "question"
    PRICING = "pricing"
    OTHER = "other"


class FeedbackAnalysis(BaseModel):
    """The structured result an LLM is asked to produce for a single piece of feedback.

    This is the contract between the LLM layer and everything downstream of it. Application
    code depends on this shape, never on a provider's raw response format.
    """

    summary: str = Field(
        ..., min_length=1, description="One or two sentence summary of the feedback."
    )
    sentiment: Sentiment
    urgency: Urgency
    category: FeedbackCategory
    recommended_action: str = Field(
        ..., min_length=1, description="A concrete next step for the team."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model's self-reported confidence, 0-1."
    )
    reasoning_short: str = Field(
        ..., min_length=1, description="One sentence of rationale, not a full chain of thought."
    )
