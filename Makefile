.PHONY: help format lint lint-fix typecheck check \
        ts-format ts-format-check ts-lint ts-lint-fix ts-typecheck ts-check \
        build clean install test all \
        up up-build down logs ps shell db-shell db-snapshot db-snapshot-full \
        db-restore db-reset migrate test-e2e

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

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

ts-format: ## Format TypeScript/React code with biome
	npm run format

ts-format-check: ## Check TypeScript/React formatting (no write)
	npm run format:check

ts-lint: ## Lint TypeScript/React code with biome
	npm run lint

ts-lint-fix: ## Lint and auto-fix TypeScript/React issues with biome
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

# ── Local dev stack (docker compose) ──────────────────────────────────────────
# Postgres + backend + frontend, all hot-reloading. See LOCAL_DEV.md.

up: ## Start the local stack (db + backend + frontend) in the background
	docker compose up -d --wait
	@echo "✓ frontend http://localhost:$${WEB_PORT:-5173}  api http://localhost:$${API_PORT:-8000}"

# The frontend mounts a *named* volume over /app/node_modules so the container
# keeps the linux tree built by `npm ci` instead of the host's. That volume
# outlives `docker compose down`, so rebuilding the image alone leaves the
# container running the OLD dependencies -- a package.json change appears to
# install and then fails at runtime with "Failed to resolve import". Dropping the
# volume here is what makes `up-build` mean what it says; it repopulates from the
# image on the next mount. `down` first because a volume in use can't be removed,
# and `-f` so a missing volume isn't an error. pgdata is untouched (no `-v`).
up-build: ## Rebuild the dev images and refresh node_modules, then start the stack
	docker compose down
	docker volume rm -f radarvan_node_modules
	docker compose up -d --build --wait
	@echo "✓ frontend http://localhost:$${WEB_PORT:-5173}  api http://localhost:$${API_PORT:-8000}"

down: ## Stop the local stack (keeps the database volume)
	docker compose down

logs: ## Tail logs from the local stack
	docker compose logs -f

ps: ## Show local stack status
	docker compose ps

shell: ## Open a shell in the backend container
	docker compose exec backend bash

db-shell: ## Open psql against the local database
	docker compose exec db psql -U radarvan -d radarvan

migrate: ## Run alembic upgrade head against the local database
	docker compose run --rm migrate

db-snapshot: ## Dump production into db_snapshots/ (skips match_details_cache rows)
	./scripts/db_snapshot.sh

db-snapshot-full: ## Dump production including the match_details_cache rows
	./scripts/db_snapshot.sh --full

db-restore: ## Load the newest snapshot into the local database
	./scripts/db_restore.sh

db-reset: ## Destroy the local database volume and re-run migrations from scratch
	docker compose down -v
	docker compose up -d --wait db
	docker compose run --rm migrate
	@echo "✓ empty local database at head"

test-e2e: ## Run the browser suite (Firefox; builds and previews the app itself)
	npm run test:e2e

ci: clean install all build ## Run full CI pipeline
	@echo "✓ CI pipeline complete!"
