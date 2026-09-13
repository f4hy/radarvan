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
- **Win prediction:** an N-model ONNX ensemble (`ml_ensemble/`) served with
  `onnxruntime` - every prediction runs all N replicates and reports the mean
  plus the spread across them; player ratings use OpenSkill.
- **Tooling:** Python ≥3.14 managed with `uv`, linted/formatted with `ruff` and
  type-checked with `mypy` (strict); TypeScript in strict mode, formatted with
  `prettier` and linted with `eslint`.

## Quick Start

The fastest path is the containerized dev stack — Postgres, backend and
frontend, all hot-reloading, against a local database you can safely break:

```bash
cp .env.example .env   # fill in AWS / cncstats / Discord keys
make up                # frontend :5173, api :8000, postgres :5433
make db-snapshot       # optional: pull production data down...
make db-restore        # ...and load it locally
```

See [LOCAL_DEV.md](LOCAL_DEV.md) for the full workflow, including how to test a
migration before it reaches production.

To run the servers directly on the host instead, install both Python and Node
dependencies:

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
  `MAPPARSE_BIN` env var. Provenance below.
- `ml_ensemble/` — the N-model win-prediction ensemble (`model-*.onnx`) and
  their shared vocabulary (`vocab.json`), read from the repo root by
  `radarvan/ml_inference.py`. Override the directory with `ML_ENSEMBLE_DIR`.
  See `ml/bootstrap_matrix.py` for how the replicates are produced.

Model-training code and its heavier dependencies live under `ml/` and are
installed only on demand (`uv sync --group ml`), never in the production app.

### `mapparse` provenance

Upstream: <https://github.com/bill-rich/mapparse>. The source is **not** vendored
here — the committed binary is the only copy in this repo, so this section is what
makes it reproducible.

| | |
| --- | --- |
| Upstream revision | `673567269893914c9a8c073f1375127e99a38242` |
| Built | 2026-07-04T19:41:54Z |
| Working tree | **dirty** (`vcs.modified=true`) — local edits not in the upstream commit |
| Toolchain | `go1.26.5`, `GOOS=linux`, `GOARCH=amd64`, `CGO_ENABLED=1` |
| SHA-256 | `f1463691d74e439058cde85b4ad960648e582b771de784e35e08d6a527ad0e8c` |

`tests/test_mapparse_provenance.py` pins the hash, so replacing the binary is a
red build rather than a silent change in map geometry. Everything in the table
above except the upstream URL is readable back off the binary itself with
`go version -m mapparse`, which is the first thing to run if this section and the
file ever disagree.

Two things follow from the dirty build. The upstream commit alone does **not**
reproduce this binary, so anyone rebuilding needs whatever local changes produced
it — recover them by diffing a clean build's `--json` output against a stored
`jsons/*.json`. And a rebuild changes the hash, which is exactly what
`MapData.mapparse_bin_hash` is for: `POST /api/reparse_maps` finds the rows parsed
by the older build. Update the table and the pinned hash in the same commit as any
new binary.

Rebuild (once the local changes are recovered):

```bash
GOOS=linux GOARCH=amd64 go build -o mapparse .
```
