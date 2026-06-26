.PHONY: install lint format test run clean

install:
	uv pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .
	mypy argus/

format:
	ruff format .
	ruff check --fix .

test:
	pytest -m "not live"

test-live:
	pytest -m "live" -v

run:
	argus --help

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
