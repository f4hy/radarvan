# Radarvan

Radarvan is a statistics-tracking application for **Command & Conquer: Generals
Zero Hour**. It scrapes published games, parses the resulting replay files (via
the `cncstats` binary) to extract per-player match data, stores everything in
PostgreSQL, and serves a wide range of statistics — player and general win/loss
records, match details (APM, spending, kill maps), leaderboards, draft
randomization, OpenSkill ratings, pairwise synergy, and an ONNX-based win
predictor — to a React single-page app.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy on PostgreSQL, Pydantic for the wire schema,
  Alembic for migrations.
- **Frontend:** React 19 + Vite + Material-UI (MUI), recharts for charts. The
  TypeScript API client under `src/api/` is auto-generated from the backend's
  OpenAPI spec (do not edit it by hand).
- **Storage:** Replay `.rep` files and their parsed JSON live in S3
  (`s3://generals-stats/radarvan/dev/`), accessed via `fsspec` / `s3fs`.
- **Win prediction:** an exported ONNX model (`ml_model.onnx`) served with
  `onnxruntime`; player ratings use OpenSkill.
- **Tooling:** Python ≥3.14 managed with `uv`, linted/formatted with `ruff` and
  type-checked with `mypy` (strict); TypeScript in strict mode, formatted with
  `prettier` and linted with `eslint`.

## Quick Start

Install both Python and Node dependencies:

```bash
make install        # uv sync + npm install
```

### Environment

The backend reads configuration from environment variables (set them in your
shell or a `.env` file):

- `DATABASE_URL` — PostgreSQL connection string (**required**).
- `DEV=1` — disables scheduled scraping; also relaxes the session cookie so login
  works over plain HTTP for local development.

Discord OAuth login needs additional variables (`DISCORD_CLIENT_ID`,
`DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`, `SESSION_SECRET`) — see the
local `auth.md` setup notes (gitignored, not part of the public tree).

### Run the backend

```bash
alembic upgrade head                 # apply database migrations
fastapi run radarvan/main.py         # start the API server (matches Procfile)
```

### Run the frontend

```bash
npm start                            # Vite dev server; proxies /api → localhost:8000
```

## Development Workflow

The [`Makefile`](Makefile) is the canonical entry point for formatting, linting,
type-checking, and CI. Run `make help` to list every target.

- `make all` — format + auto-fix lint + type-check across both Python and TypeScript (run before pushing)
- `make check` — Python lint + mypy
- `make ts-check` — TS format-check + ESLint + tsc
- `make test` — `uv run pytest`
- `make build` — checks for both languages, then `uv build`
- `make ci` — full pipeline: `clean install all build`

To regenerate the TypeScript API client after changing backend routes, start the
FastAPI dev server and run `./gen_client.sh`.

## Architecture

[`CLAUDE.md`](CLAUDE.md) is the comprehensive guide to the codebase — module
layout, data flow, key patterns, and gotchas. Other docs cover specific
subsystems:

- [`SYNERGY_METHODOLOGY.md`](SYNERGY_METHODOLOGY.md) — the statistical
  methodology behind the player-synergy stats (ridge logistic regression over the
  rating model's log-odds).
- `auth.md` — Discord OAuth2 login setup (app registration, env vars, the
  `users` table migration). Kept as a local, gitignored doc.

## Deployment

Production runs on Heroku (`radarvan-5e9c302c60e6.herokuapp.com`). The `Procfile`
launches the FastAPI server, which also serves the built frontend as static
files.

## Repository Artifacts

A few binary/data artifacts are intentionally committed to the repo because the
deployed Heroku server loads them at runtime and there is no separate artifact
store wired up:

- `mapparse` — a map-geometry parser binary that `radarvan/missing_maps.py` and
  `radarvan/map_upload.py` shell out to. Override its location with the
  `MAPPARSE_BIN` env var.
- `ml_model.onnx` / `ml_model_vocab.json` — the exported win-prediction model and
  its vocabulary, read from the repo root by `radarvan/ml_inference.py`. Override
  with the `ML_MODEL_PATH` / `ML_VOCAB_PATH` env vars.

Model-training code and its heavier dependencies live under `ml/` and are
installed only on demand (`uv sync --group ml`), never in the production app.
