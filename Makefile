.PHONY: install lint format typecheck test

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
