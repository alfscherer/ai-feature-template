.PHONY: install lint format typecheck test eval

install:
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	black .
	ruff check --fix .

typecheck:
	mypy app

test:
	pytest

# Hits real LLM APIs; needs a provider key in .env. See docs/evaluation.md.
eval:
	python -m evals.run $(ARGS)
