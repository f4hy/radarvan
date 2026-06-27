.PHONY: help format lint lint-fix typecheck check \
        ts-format ts-format-check ts-lint ts-lint-fix ts-typecheck ts-check \
        build clean install test all

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python and Node dependencies
	uv sync
	npm install

# ── Python ────────────────────────────────────────────────────────────────────

format: ## Format Python code with ruff
	uv run ruff format radarvan/

lint: ## Lint Python code with ruff
	uv run ruff check radarvan/

lint-fix: ## Lint and auto-fix Python issues with ruff
	uv run ruff check --fix radarvan/

typecheck: ## Type-check Python code with mypy
	uv run mypy radarvan/

check: lint typecheck ## Run all Python checks (no formatting)
	@echo "✓ Python checks passed!"

# ── TypeScript / React ────────────────────────────────────────────────────────

ts-format: ## Format TypeScript/React code with prettier
	npm run format

ts-format-check: ## Check TypeScript/React formatting (no write)
	npm run format:check

ts-lint: ## Lint TypeScript/React code with ESLint
	npm run lint

ts-lint-fix: ## Lint and auto-fix TypeScript/React issues with ESLint
	npm run lint:fix

ts-typecheck: ## Type-check TypeScript code with tsc
	npm run typecheck

ts-check: ts-format-check ts-lint ts-typecheck ## Run all TypeScript checks (no formatting)
	@echo "✓ TypeScript checks passed!"

# ── Combined ──────────────────────────────────────────────────────────────────

all: format lint-fix typecheck ts-format ts-lint-fix ts-typecheck ## Format, lint, and type-check all code
	@echo "✓ All formatting and checks complete!"

build: check ts-check ## Build after running all checks
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

test: ## Run tests
	uv run pytest

ci: clean install all build ## Run full CI pipeline
	@echo "✓ CI pipeline complete!"
