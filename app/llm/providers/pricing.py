# Approximate USD prices per 1M tokens, captured at commit time from each provider's public
# pricing page. Prices change without notice; treat this as a rough cost signal for
# observability and evaluation, not as a billing-grade source of truth.
_PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
}


def estimate_cost_usd(model: str, *, input_tokens: int, output_tokens: int) -> float | None:
    """Returns None for unknown models rather than guessing."""
    pricing = _PRICING_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        return None

    input_price_per_million, output_price_per_million = pricing
    return (input_tokens / 1_000_000) * input_price_per_million + (
        output_tokens / 1_000_000
    ) * output_price_per_million
