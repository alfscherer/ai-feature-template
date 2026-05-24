// Mirrors app/llm/schemas/feedback.py and app/api/schemas.py. Kept as plain types, not
// generated, since the backend contract changes slowly enough that a codegen step (e.g. from
// the OpenAPI schema FastAPI already exposes at /openapi.json) would be more machinery than
// this one screen needs -- see docs/frontend.md.

export type Sentiment = "positive" | "negative" | "neutral" | "mixed";
export type Urgency = "low" | "medium" | "high" | "critical";
export type FeedbackCategory =
  | "bug"
  | "feature_request"
  | "praise"
  | "complaint"
  | "question"
  | "pricing"
  | "other";

export interface FeedbackAnalysis {
  summary: string;
  sentiment: Sentiment;
  urgency: Urgency;
  category: FeedbackCategory;
  recommended_action: string;
  confidence: number;
  reasoning_short: string;
}

export interface AnalyzeMetadata {
  request_id: string;
  provider: string;
  model: string;
  prompt_version: string;
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  degraded: boolean;
}

export interface AnalyzeResponse {
  analysis: FeedbackAnalysis;
  metadata: AnalyzeMetadata;
}
