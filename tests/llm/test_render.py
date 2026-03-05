from app.llm.prompts.render import render_feedback_analysis_prompt


def test_prompt_includes_feedback_and_schema() -> None:
    prompt = render_feedback_analysis_prompt(feedback="The app crashed on save.", context=None)

    assert "The app crashed on save." in prompt
    assert "recommended_action" in prompt
    assert "(none provided)" in prompt


def test_prompt_includes_context_when_given() -> None:
    prompt = render_feedback_analysis_prompt(
        feedback="Great job!", context="Enterprise plan customer"
    )

    assert "Enterprise plan customer" in prompt
