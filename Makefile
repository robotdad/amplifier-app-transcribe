.PHONY: install check test clean

install:
	uv sync

check:
	@echo "Running linting and type checks..."
	uv run ruff check src/ tests/ || true
	uv run ruff format --check src/ tests/ || true
	uv run pyright src/ tests/ || true

test:
	uv run pytest tests/ -v

clean:
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
