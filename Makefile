.PHONY: help format lint typecheck check build clean install test all

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies using uv
	uv sync

format: ## Format code with ruff
	uv run ruff format radarvan/

lint: ## Lint code with ruff
	uv run ruff check radarvan/

lint-fix: ## Lint and auto-fix issues with ruff
	uv run ruff check --fix radarvan/

typecheck: ## Run mypy type checking
	uv run mypy radarvan/

check: lint typecheck ## Run all linting and type checking (without formatting)
	@echo "✓ All checks passed!"

all: format lint-fix typecheck ## Format, lint with fixes, and type check
	@echo "✓ All formatting and checks complete!"

build: check ## Build the package
	uv build
	@echo "✓ Package built successfully!"

clean: ## Clean build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleaned all build artifacts and caches!"

test: ## Run tests (add your test command here)
	@echo "Add your test command (e.g., uv run pytest)"
	# uv run pytest

ci: clean install all build ## Run full CI pipeline
	@echo "✓ CI pipeline complete!"
