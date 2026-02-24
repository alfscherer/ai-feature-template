from app.llm.providers.pricing import estimate_cost_usd


def test_known_model_returns_nonzero_cost() -> None:
    cost = estimate_cost_usd("gpt-4o-mini", input_tokens=1000, output_tokens=500)

    assert cost is not None
    assert cost > 0


def test_unknown_model_returns_none() -> None:
    assert estimate_cost_usd("not-a-real-model", input_tokens=100, output_tokens=100) is None
