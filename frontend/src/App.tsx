import { useState } from "react";
import { ApiError, analyzeFeedback } from "./api";
import type { AnalyzeResponse } from "./types";

const MAX_FEEDBACK_LENGTH = 4000;

export default function App() {
  const [feedback, setFeedback] = useState("");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!feedback.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      setResult(await analyzeFeedback(feedback, context));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <h1>AI Feedback Analyzer</h1>
      <p className="subtitle">
        Paste a piece of customer feedback below. This calls the same <code>/api/analyze</code>{" "}
        endpoint documented in the README, with production concerns (retries, caching,
        structured output validation) applied the same way they would be for a real client.
      </p>

      <form onSubmit={handleSubmit} className="form">
        <label htmlFor="feedback">Feedback</label>
        <textarea
          id="feedback"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          maxLength={MAX_FEEDBACK_LENGTH}
          rows={6}
          placeholder="e.g. The export button crashes the app every time I click it."
          required
        />

        <label htmlFor="context">Context (optional)</label>
        <input
          id="context"
          type="text"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="e.g. Plan: Enterprise, Platform: iOS"
        />

        <button type="submit" disabled={loading || !feedback.trim()}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      {error && <div className="error">{error}</div>}
      {result && <ResultView result={result} />}
    </main>
  );
}

function ResultView({ result }: { result: AnalyzeResponse }) {
  const { analysis, metadata } = result;

  return (
    <section className="result" aria-label="Analysis result">
      {metadata.degraded && (
        <div className="degraded-banner">
          The model's response didn't validate even after a repair attempt. This is a fallback
          result, not a real analysis.
        </div>
      )}

      <div className="badges">
        <span className={`badge sentiment-${analysis.sentiment}`}>{analysis.sentiment}</span>
        <span className={`badge urgency-${analysis.urgency}`}>{analysis.urgency} urgency</span>
        <span className="badge category">{analysis.category.replace("_", " ")}</span>
      </div>

      <p className="summary">{analysis.summary}</p>

      <dl className="fields">
        <dt>Recommended action</dt>
        <dd>{analysis.recommended_action}</dd>
        <dt>Reasoning</dt>
        <dd>{analysis.reasoning_short}</dd>
        <dt>Confidence</dt>
        <dd>{Math.round(analysis.confidence * 100)}%</dd>
      </dl>

      <footer className="metadata">
        {metadata.provider}/{metadata.model} (prompt {metadata.prompt_version}) &middot;{" "}
        {Math.round(metadata.latency_ms)}ms
        {metadata.input_tokens !== null && metadata.output_tokens !== null && (
          <>
            {" "}
            &middot; {metadata.input_tokens}+{metadata.output_tokens} tokens
          </>
        )}
        {metadata.estimated_cost_usd !== null && (
          <> &middot; ~${metadata.estimated_cost_usd.toFixed(5)}</>
        )}
      </footer>
    </section>
  );
}
