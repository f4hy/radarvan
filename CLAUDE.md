# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

`make help` lists every target. `make all` — format + auto-fix lint + type-check **both** Python and TypeScript; run this before pushing.

**Client codegen**: `./gen_client.sh` regenerates the TypeScript client in `src/api/` from the running server's OpenAPI spec — the FastAPI server must already be running and serving your changed code. Always use this script (not `npm run openapi-ts` or a manual generator invocation). Never hand-edit `src/api/` (auto-generated). `PlayerEnum.ts` reorders on every regen (Python set iteration) — that churn is normal.

## Dev workflow

- The dev servers are **already running** in the user's own terminals: Vite on 5173 (proxying `/api`), FastAPI on 8000 (auto-reloads on edit). Never launch your own instances to verify changes — connect to the running ones. Those hand-run servers use the `DATABASE_URL` from `.env`, which points at **production** Postgres — treat writes through them accordingly. `make up` starts an alternative local stack with its own Postgres (`LOCAL_DEV.md`) — the safe place to try schema changes — but binds the same ports, so it and the hand-run servers can't both be up unless `API_PORT`/`WEB_PORT` are set.
- **Migrations**: alembic revisions apply themselves on deploy and the chain cannot build a schema from an empty database. Invoke the **`db-migrations`** skill before writing one.
- Do not commit or push (and don't ask to) unless explicitly told. Finish the work, report what changed, and leave it in the working tree.
- **Fetching real data (a match, replay, player stats, etc.) to inspect or verify something: use the running API at `http://localhost:8000` (`curl`), not a direct DB/S3 connection.**
- Read the source file directly rather than chaining several `grep`/`sed`/`awk` shell commands. Use `grep`/`Bash` only for repo-wide searches; once you know the file, read it.
- **Playwright (MCP tool or `e2e/` tests) must use Firefox — never Chrome/Chromium.** Driving the UI and `/api` cache behaviour are covered by the **`run-radarvan`** skill.
- **Never call `GET /api/matchup_commentary/` (or anything that reaches `matchup_commentary.generate_commentary`) without asking first — a cache *miss* still generates and spends real tokens/money**, against whichever provider `COMMENTARY_PROVIDER` currently selects. Each call needs its own explicit confirmation. Use the free `GET /api/matchup_commentary/prompt_preview` for prompt content/size/structure instead.
- **Same rule for `POST /api/generate_game_night_summary/{night}`, `POST /api/backfill_game_night_summaries`, `POST /api/generate_match_blurbs/{night}` and `POST /api/backfill_match_blurbs` (`max_to_update=0` is a free dry run)** — the only other routes that bill a call. Every read path for those features (`GET /api/game_night/{night}`, `GET /api/narrative/{id}`) is free and never generates; the nightly scheduler is the only other caller.

See `ENVIRONMENT.md` for environment variables.

## Architecture

Backend lives in `radarvan/` — the layout is self-describing, read the module you need. What isn't obvious from the file itself:

- **`api_types/` is the canonical wire schema** (a package, one module per domain — `players.py`, `matches.py`, `bracket.py`, etc.). TS types are generated from the resulting OpenAPI spec, so change the Pydantic model, not the generated client.
- **`cncstats_model/zhreplay.py`'s `EnhancedReplayV2` is the only replay type to import** — `cncstats_types.py`/`cncstats_types_v2.py` are unused reference copies.
- **Prefer the specific repo in `repositories/`** over the `ReplayManager` facade in `db_utils.py`; the facade exists for legacy callers.
- **`main.py` is app composition only** (middleware order, router registration, lifespan, the global exception handler, static serving). Handlers go in `routes/`.
- **ML inference is ONNX Runtime only — no torch in prod** (`ml_inference.py`, `winprob_inference.py`).
- **Rating *levels* are never shown to a normal visitor** — a rating number, ordinal, or leaderboard position must not reach the Records page, a profile, a match view, or commentary. See the `player-ratings-and-roles` skill before surfacing anything rating-derived.

Data flow: replays arrive by scheduled scrape or `POST /api/upload_replay` → cncstats parses the `.rep` → `.rep`+parsed JSON go to S3, rows to Postgres → derived data is cached and served via REST, consumed by the generated client.

## Python conventions

- **This is Python 3.14** (`requires-python = ">=3.14"`). Unparenthesized `except ValueError, TypeError:` is valid — [PEP 758](https://peps.python.org/pep-0758/) — and `ruff format` actively rewrites the parenthesized form to it. That is correct, current code: do not "fix" it back, and never report it as a syntax error.
- **Exception: any `radarvan/` module reachable from `ml/` must stay parseable by Python 3.13** (torch has no 3.14 wheel; training runs in `.venv-ml`). There, PEP 758's bare form *is* a SyntaxError — keep those `except` clauses parenthesized and tagged `# fmt: skip` (`player_role.py` is the live example). Many modules open with `from __future__ import annotations` for the same reason (PEP 649 only defers annotation evaluation by default on 3.14+) — that's repo-wide and load-bearing; don't add a comment re-explaining it in individual files.
- **Never use `TYPE_CHECKING`** — resolve circular imports by moving code to a module that already has access to all needed types.
- **Never mutate function inputs** — return new values (`model_copy(update=...)` for Pydantic).
- camelCase wire aliases with `populate_by_name`. Don't add `slots=True` to a `BaseModel`'s `ConfigDict` expecting a memory win — it's silently ignored for `BaseModel`.
- **Default to short minimal comments, and no multi-line docstrings.** Add a comment only for something that would still be non-obvious to someone reading this code cold on an unrelated task — a hidden constraint, a subtle invariant, a workaround for a specific bug — not what the code does or why *this task* touched it. If it would age out the moment the current task is forgotten, it doesn't belong in the source.
- **This rule beats the surrounding code.** Roughly 60% of existing docstrings here are multi-line, some 30+ lines; that is legacy, not the house style, and "match the surrounding idiom" does not apply to comment length. Match the neighbours on naming and structure, never on verbosity — write the short version next to the long ones. Shorten what you touch; don't expand to fit.

Docs elsewhere in the repo: `auth.md` (Discord OAuth setup), `SYNERGY_METHODOLOGY.md`, `ml/model_design.md`, `LOCAL_DEV.md`. `radarvan/api_types/` is the source of truth for the wire format.
