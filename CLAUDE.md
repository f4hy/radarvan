# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radarvan is a statistics tracker for Command & Conquer: Generals Zero Hour. A FastAPI backend scrapes/accepts game replays, parses them via the external cncstats service, stores results in PostgreSQL + S3, and serves stats; a React frontend renders them. Production runs on Heroku (radarvan-5e9c302c60e6.herokuapp.com).

## Commands

The `Makefile` is the canonical entry point; `make help` lists every target. Local dev stack targets (`up`, `down`, `logs`, `db-shell`, `db-snapshot`, `db-restore`, `db-reset`) are documented in `LOCAL_DEV.md`.

- `make all` — format + auto-fix lint + type-check **both** Python and TypeScript; run this before pushing.
- Python tests live in `tests/`, fixture JSONs alongside them. Only `/api` is proxied to localhost:8000 by the Vite dev server (`vite.config.ts`).

**Client codegen**: `./gen_client.sh` regenerates the TypeScript client in `src/api/` from the running server's OpenAPI spec — the FastAPI server must already be running and serving your changed code. Always use this script (not `npm run openapi-ts` or a manual generator invocation). Never hand-edit `src/api/` (auto-generated). `PlayerEnum.ts` reorders on every regen (Python set iteration) — that churn is normal.

### Dev workflow

- The dev servers are **already running** in the user's own terminals: Vite on 5173 (proxying `/api`), FastAPI on 8000 (auto-reloads on edit). Never launch your own instances to verify changes — connect to the running ones (confirm with `curl`/`ss -ltnp` if unsure). Never run broad `pkill -f vite` / `pkill -f fastapi`; if a stray process must be killed, target the exact PID. Those hand-run servers use the `DATABASE_URL` from `.env`, which points at **production** Postgres — treat writes through them accordingly.
- **`docker compose up` (`make up`) is the alternative: the same two servers plus a local Postgres**, documented in `LOCAL_DEV.md`. Compose overrides `DATABASE_URL` to its own container, so it is the safe place to try schema changes. `make db-snapshot` + `make db-restore` hydrate it from production (read-only `pg_dump`, skipping `match_details_cache` rows, which the app regenerates from S3). It binds the same 8000/5173 by default, so it and the hand-run servers can't both be up unless `API_PORT`/`WEB_PORT` are set in `.env`.
- **The migration chain cannot build the schema from an empty database** — the initial revision is an empty `pass` (alembic was stamped onto the pre-existing prod DB), so later revisions ALTER tables nothing ever created. `scripts/bootstrap_db.py` (what the compose `migrate` service runs) branches on this: `alembic upgrade head` when `alembic_version` exists, `Base.metadata.create_all()` + `alembic stamp head` when the database is empty. A new migration is therefore tested against a *restored snapshot*, not an empty database.
- **Production migrations run themselves, on deploy.** The `Procfile` has a `release: alembic upgrade head` phase, so pushing to Heroku applies any pending revision before the new dynos start; a failing migration fails the release and the old code keeps serving. Three things this depends on, each of which broke it once: `alembic` must stay in `[project] dependencies` (Heroku's buildpack installs `uv sync --no-dev`, so the dev group is not in the slug); `alembic/env.py` normalizes `postgres://` → `postgresql://` itself, because `alembic upgrade` re-reads the raw env var in its own process and Heroku's addon-managed URL uses the legacy scheme; and it prints the DSN **redacted**, since release-phase output is app log anyone with access can read. The release phase deliberately runs bare `alembic upgrade head` rather than `scripts/bootstrap_db.py` — that script's empty-database branch (`create_all` + `stamp head`) is there for a fresh *local* volume, and on production it would silently manufacture a schema instead of failing loudly if `DATABASE_URL` ever pointed somewhere empty.
- **A migration still has to be backward-compatible with the running code.** Release phase applies it while the *old* dynos are still serving, so an additive change (a new table, a nullable column) is safe, while a drop or a rename breaks requests in the window before the swap. Split those into two deploys.
- Do not commit or push (and don't ask to) unless explicitly told. Finish the work, report what changed, and leave it in the working tree — the user manages commits.
- **Fetching real data (a match, replay, player stats, etc.) to inspect or verify something: use the running API at `http://localhost:8000` (`curl`), not a direct DB/S3 connection.** The service is always running; it's the intended read path and matches what the frontend actually sees. Reserve direct `DatabaseManager`/`replay_files` scripting for cases the API genuinely can't express.
- **When exploring code, read the source file directly (`Read` tool) rather than chaining several `grep`/`sed`/`awk` shell commands.** Use `grep`/`Bash` only for repo-wide searches (finding *where* something is defined/used across many files) — once you know the file, read it.
- **Playwright (MCP tool or `e2e/` tests) must use Firefox — never Chrome/Chromium.** Pass the Firefox browser/channel explicitly wherever the driver defaults to Chromium. The bundled Playwright MCP server here defaults to a Chromium build (`chrome` channel) that isn't installed on this host, so it errors out on launch — drive Firefox directly instead (`const { firefox } = require('@playwright/test')` from the project root, so `node_modules` resolves).
- **Easiest way to inspect one specific match (including its map render) is the DebugData page**, not the Matches list: `http://localhost:5173/?page=debug-data`, then enter the match ID in the `matchId` field and submit — it works via direct URL even though the sidebar link itself is admin-gated (`status.user.is_admin`), and it sidesteps the Matches page's `exclude_dev=true` filtering (which hides `is_dev` matches — e.g. locally-uploaded test replays — unless you're logged in as admin).
- **Browser caching of `/api` responses is a flat 60s** (`dependencies.cache_short`, `Cache-Control: private, max-age=60`); the built frontend is handled by `http_cache.CachedStaticFiles` (hashed `/assets/*` immutable for a year, everything else `no-cache`). After reparsing/changing stored map geometry or match data, a reload picks it up within a minute — no hard-refresh needed.
- **Never call `GET /api/matchup_commentary/` (or anything that reaches `matchup_commentary.generate_commentary`) without asking first — it is a GET, but a cache *miss* still generates. — it spends real tokens/money on every call, against whichever provider `COMMENTARY_PROVIDER` currently selects (Anthropic or Gemini).** Each individual call needs its own explicit confirmation from the user; a prior "yes" doesn't cover the next one. Use the free `GET /api/matchup_commentary/prompt_preview` instead for anything about prompt content/size/structure — it builds the exact same payload without calling either provider.
- **Same rule for `POST /api/generate_game_night_summary/{night}`** — the one hand-trigger for the nightly game-night recap, and the only other route that bills a call. Every read path for that feature (`GET /api/game_night/{night}`) is free and never generates; `commentary/night_summary.build_prompt` renders the exact payload for inspection without a provider call.

### Environment variables

See `ENVIRONMENT.md` for the full table (including the `CNCSTATS_APIKEY` vs `CNCSTATS_API_KEY` distinction, which are two different services).

## Architecture

### Backend (`radarvan/`)

Read the module you need — the layout is self-describing. What isn't:

- **`api_types.py` is the canonical wire schema.** TS types are generated from the resulting OpenAPI spec, so change the Pydantic model, not the generated client.
- **`cncstats_model/zhreplay.py`'s `EnhancedReplayV2` is the only replay type to import** — `cncstats_types.py`/`cncstats_types_v2.py` are unused reference copies.
- **Prefer the specific repo in `repositories/`** over the `ReplayManager` facade in `db_utils.py`; the facade exists for legacy callers.
- **`main.py` is app composition only** (middleware order, router registration, lifespan, the single global exception handler, static serving). Handlers go in `routes/`.
- **`queries/` owns corpus selection; `routes/` owns HTTP.** A handler that computes over matches should declare the corpus it needs in its signature — `games: CompetitiveGames`, `AllGames`, `WindowedCompetitiveGames`, `UnfilteredCompetitiveGames` — and never take a `ReplayManager`. The `game_format` query parameter comes with the dependency. The plain functions (`queries.competitive_games(replay_manager, …)`) are for callers that aren't a request. **Don't use the dependency form when a handler can avoid the work** — a FastAPI dependency is resolved before the handler runs, so `routes/players.balance_teams` (whose 6h hold answers most requests without touching the corpus) deliberately keeps its `ReplayManager` and calls the plain function on a miss.
- **Anything other than a route that wants a route's answer means the answer is a read model**, and it belongs in `queries/` — not in a handler that other modules import. `commentary/matchup_commentary.py` used to call `routes.players` handlers as functions, passing `replay_manager=` into an HTTP handler and `asyncio.run`-ing an endpoint; that made handler signatures an internal API. `queries/players.py` holds the two shared ones (`player_ratings_payload`, `player_head_to_head_detail`). Import direction is `routes` → `queries` → `cache`/`repositories`; nothing in `queries/` may import from `routes/`.
- **Three projections of an existing cache, not new derivations.** `match_narrative.py` (a match retold as ordered beats), `game_night.py` (an evening's records + highlight cards) and `durations.py` (the game-length histogram) all compute from data already parsed — `MatchDetails` and `MatchInfo` — the way `routes/matches.get_build_orders` does. None of them carries a version or touches `DETAILS_VERSION`, so adding a beat or a highlight costs nothing and invalidates nothing. Keep them pure: the corpus selection and detail loading live in `queries/game_night.py`, which is what lets the scheduler and the route describe the same night.
- **ML inference is ONNX Runtime only — no torch in prod** (`ml_inference.py`, `winprob_inference.py`).

### Auth model (three tiers)

1. Most `/api` routers require `X-API-Key` (`verify_api_key`), which accepts **either tier** — the HTTP method is irrelevant. A route needing the **admin** tier opts in explicitly with `dependencies=ADMIN_ONLY` (i.e. `Depends(require_admin_key)`). Only two are left there (`POST`/`DELETE /api/map_data/{map_name}`, `POST /api/test_tournament_report/…`) — every other ops endpoint now lives on a cookie-session router, see (2). Normal tier covers everything the app itself does, including `POST /api/upload_replay`, draft randomization, and prediction. Only enforced when `ENFORCE_AUTH` is set; with no keys configured at all, auth is off. `has_admin_access` is the boolean form, for a normal-tier route with an admin-only *option* (commentary's `force_refresh`). `tests/test_auth_tiers.py` fails if a new mutating route picks none of the three gates.
2. Cookie-session routes (Discord OAuth): `routes/auth.py`, `votes.py`, `map_upload.py`, `bracket.py` writes, and the `session_router` in `admin.py`/`files.py`/`maps.py`/`profile.py`/`superlatives.py`/`tournaments.py` — deliberately **not** behind the API key; identity via signed session cookie. **Any admin action the UI drives belongs here, never on the API-key router**: the frontend ships one key to every visitor, so it can only ever be normal-tier, and the baseline gate would reject a cookie-only request before the route's own gate ran.

   Three separate admin sets, on purpose: `player_ids.ADMIN_PLAYERS` (debug views), `TOURNAMENT_ADMINS` (bracket only), `OPS_ADMINS` (operational tasks). The matching gates are `require_admin_login` (`dependencies=ADMIN_LOGIN`) and `require_ops_admin` (`dependencies=OPS_ADMIN`); both share `_require_logged_in_admin`, differing only in the membership test. `ADMIN_LOGIN` covers `POST /api/reparse/{match_id}` (the DebugData button); `OPS_ADMIN` covers everything the **admin control panel** (`src/AdminPanel.tsx`, `?page=admin-panel`) runs — scrape, register, bulk reparse, backfill, recompute, override, delete. Both also accept an admin-tier key so curl/ops scripts keep working against the same paths, and read that header off the request instead of declaring it as a `Security` param — declaring it would wrongly advertise APIKeyHeader as the route's security scheme in the OpenAPI spec.

   `test_auth_tiers.py` sweeps this structurally rather than by allowlist: every cookie-gated route must sit on a `session_router`, every `session_router` route must carry one of the two cookie gates, and neither may advertise APIKeyHeader. Adding a `session_router` to a new module means including it in `main.py` **without** `PROTECTED`.
3. `maps.public_router` (map images) — no auth, because browsers load them via `<img src>`.

**Rating *levels* are not public.** A player's rating number — `NamedRating.ordinal()`, and anything derived from it: `ordinal_high`, `ordinal_low`, `mu`, a leaderboard position — is deliberately kept off every page a normal visitor sees. "Player Ratings" and "Player Synergy" are hidden from the sidebar behind `status.user.is_admin` (`src/Menu.tsx`) for exactly this reason. It is a soft gate — the route is still reachable by URL and `/api/player_ratings/` is normal-tier — so **the gate is the page, and a rating that escapes onto another page defeats it entirely**. Do not surface a rating level on the Records page, a player profile, a match view, commentary, or anything else public, however it is scaled or framed ("all-time peak", "career high", "rank #1 at 330").

What *is* fine, and already shipped: a rating **change** (`📈 Biggest Rating Gain (30d)` is `round(delta * 10)`), a **win probability** (`🐍 Biggest Upset`), and plain W-L records. Those say who is playing well without publishing the ladder. The distinction is level vs. delta — if a number would let someone reconstruct the leaderboard, it is a level.

This is not a new rule — commentary reached the same conclusion independently. `commentary_prompts.py` tells the model the ratings block is "internal - never seen by users anywhere else in the app - so never state them, or a derived rank/position, in the output", and `HypeRatingsContext` exists because embedding the two players' own ordinals let the model quote one. `queries/players.player_ratings_payload` is the one place a level is meant to reach the wire, and it feeds only the admin-gated ratings page.

`tests/test_superlatives_records.py::test_no_record_exposes_a_rating_level` guards the records path by feeding `ordinal_high`/`ordinal_low` a sentinel and asserting it reaches no card, so a new record reaching for them fails there rather than in review. Nothing enforces it on the other surfaces — check by hand when you add one.

### Data flow

1. Replays arrive by scheduled gentool scrape or `POST /api/upload_replay`.
2. cncstats parses the `.rep`; the `.rep` and parsed JSON go to S3 (`s3://generals-stats/radarvan/dev/`), rows to Postgres (`ReplayFile` → `ParsedReplayJson` → `Match`+`MatchPlayer`+`MatchCompostion`).
3. Derived data is cached (in-process + `match_details_cache` table) and served via REST; the React app consumes it through the generated client.

### Frontend (`src/`)

React + MUI + recharts, entry `index.tsx` → `App.tsx` → `Menu.tsx`; views map ~1:1 to backend areas. Frontend-specific conventions and gotchas live in `src/CLAUDE.md`, which loads automatically when you work in that directory.

## Core invariants — read before writing backend code

**DB sessions and threads.** The request-scoped session comes from `Depends(get_replay_manager)`. Anything that outlives the request must open its own session via `db_manager.get_replay_manager()` (context manager): FastAPI runs background tasks *after* yield-dependency teardown, and scheduler jobs each open a fresh session per run (a shared long-lived session poisons every later job after one failed transaction). Never let session-bound ORM objects cross into `asyncio.to_thread` workers — extract plain values first (see `matches.ReparseInputs`) or use the per-thread loaders `match_details.load_many_match_details` / `superlatives.load_many_superlative_data`. When catching DB errors inside a loop and continuing, call `session.rollback()` in the except branch or every subsequent statement fails with `PendingRollbackError` (see `matches.register_matches`).

**`update_match` needs a detached Match.** `MatchRepo.update_match` clears `existing.players` then merges. Only ever pass it a fresh Match built by `replay_to_db_match` — passing a session-attached instance is the same object via the identity map, and the clear + delete-orphan cascade permanently deletes the match's players.

**Event loop.** Async handlers and scheduler jobs must push blocking work (cncstats HTTP, S3 I/O, heavy computation) through `asyncio.to_thread`. Sequential `to_thread` calls may share one session; concurrent ones must not.

**Derivations, not caches.** Every in-process memoization goes through `@derived` (`radarvan/derived/`). Do not reach for `cachetools` directly — `tests/test_derived_registry.py` fails on a new `LRUCache`/`TTLCache`/`@cached` anywhere in `radarvan/`, against a three-entry allowlist.

```python
@derived(on=CORPUS, maxsize=6)    # def compute_player_ratings(games)
@derived(on=MAPS, maxsize=1)      # def map_name_index(replay_manager)
```

`@derived(on=…, maxsize=…)` is the entire vocabulary — there is no `key=`, no `revision=`, and deliberately no `ttl=` (a TTL is a guess at a version token, and the registry has the real one). `maxsize` is required and the lock is supplied, so an unbounded or unlocked cache cannot be declared.

`on=` names the input (`CORPUS`, `MAPS`, `MODEL`); its version token is folded into every key, so a stale entry becomes *unreachable* rather than something somebody has to remember to clear. **Every other parameter is the per-call key**, read off the signature at decoration time — forgetting a key would give *wrong* answers rather than stale ones, so it isn't something a call site gets to declare.

A token is `(epoch, revision)` and needs both halves. The epoch is a process-local counter bumped by `invalidate()`, which is what catches a reparse or a `WinnerOverride` (they change match *content* without moving `matches.created_at`). The revision is how *this call* reveals its generation, and `CORPUS` offers two ways: a `replay_manager` parameter (probed on a 60s DB poll, which also catches new matches landing outside this process) or a `games` parameter (the `list[MatchInfo]` itself, reduced to its ids). Which one applies is decided from the signature — so those two parameter names are load-bearing, and a rename fails on import rather than at runtime.

Call `cache.invalidate_match_caches()` after anything that changes match data (registers, reparses, overrides, resets). It bumps `CORPUS` and `MAPS` and triggers a background re-warm on the single warm thread — it names no cache, so a derivation added tomorrow is covered without editing it.

**The two match sets.** `cache.sorted_deduped_matches` = all games (use for counts/listings); `cache.competitive_matches` = complete + `competitive_game_filter` (balanced, non-comp-stomp, team game, ≤1 CPU) + every team has a known player (use for W/L, ratings, records). Both are `@derived(on=CORPUS)` over `replay_manager`, so they refresh when new matches land. `filter_by_format` lives in `matches.py` (it operates on `list[MatchInfo]`), not `game_composition.py`.

**Which 1v1s count, and for what.**

| set | rule | 1v1s included |
|---|---|---|
| ratings + synergy | `player_rating.is_ratable_team_game` | tournament only (`is_tournament_1v1`) |
| ML training | `ml.snapshot.is_training_match` | same — it delegates to the rule above |
| `competitive_matches` (W/L, records) | `competitive_game_filter` | all of them — a 1v1 has `is_team_game=True` |

A tournament link is the only "played to win" signal available: it's written by `tournament_membership.sync_links` for a scheduled bracket slot, or by an admin, so a practice game can't earn one. Casual 1v1s stay out of both ratings and training — that was measured, not assumed: the corpus is 55% one pairing (CoreDawg vs Syn, 115–10 over 125 games), and adding casual 1v1s cost held-out team-game AUC monotonically (0.556 → 0.538 with that pairing dropped, → 0.517 with everything). Full numbers in `ml/model_design.md`. Measure before widening any of these — the temporal split cuts over non-1v1 games, so the dev set stays byte-identical across variants and ensembles are directly comparable.

**Player roles — never re-derive them.** Whether a slot is a human, an AI, or a spectator comes from the replay header (`type == "C"` for AI; a spectator is a type-`"H"` slot with `playerTemplate` `-2`) and is persisted as `match_players.role` (`player_role.PlayerRole`). There is exactly **one** way to ask, and adding a second is a bug: build a `game_composition.MatchRoster` and read its partitions.

- `MatchInfo.roster()` — from a match (the common case; build once per match, it materializes everything up front)
- `MatchRoster.from_db_players(rows)` — from `match_players`
- `MatchRoster.from_header_players(header.metadata.players)` — at parse time, before anything is in the DB

Partitions: `.observers`, `.competitors` (played; teamless slots included), `.participants` (competitors with `team > 0`), `.humans`, `.cpus`, `.human_participants`, `.teams`. `RosterSlot.has_known_general` is separate on purpose — that's parse quality, not role, and conflating the two is what the old `is_real()` did.

Name-set questions go through the roster's own methods — `human_participant_names()` (the humans who played) and `competitor_names()` (humans + AI, no spectators) — for the same reason `all_teams_have_group_player` is a method: taking the partition from `self` is what stops a call site from asking over `slots`.

**Observers must never change an answer about the match.** Categorization, ratability, and per-player stats are properties of who *played*, so adding or removing a spectator has to be a no-op — the one exception is `GameComposition.total_players`, which counts every slot by design. This has broken twice: `filter_for_rating` read every slot, so a caster account named for the matchup (`Gorn.v.131`, not in `PLAYER_NAMES`) made 23 real games unratable; and the win-streak pass counted a spectator's `won=False` slot as a loss. `tests/test_observer_invariance.py` asserts the property directly (same answer with and without the observer, rather than a fixed expected value) — extend it when you add a filter.

Do **not** write `p.team > 0`, `p.team == Team.OBSERVER`, or a name check against a CPU list at a call site. The codebase previously spelled the observer test three inconsistent ways and carried four disagreeing CPU detectors; AI slots named outside a five-entry list (Tactical AI, EasyArmy, MediumArmy) were counted as humans in 417 matches, which put comp-stomps on the competitive leaderboards. Guessing from the player's *name* survives only as `player_role.resolve_role`'s fallback for un-backfilled rows — the header is authoritative, and an AI's header name is empty. `role` is still nullable; tighten to NOT NULL once `list_matches_with_unset_roles` returns empty (blocked on one match — see the `Team` enum note below).

**`Team` stops at `FOUR`.** `utils.determine_team` raises `ValueError: 5 is not a valid Team` for any replay with 4+ teams, so such a match can't be parsed or reparsed. The header carries 8 slots, so a full FFA needs `Team` up to `EIGHT`. One known match (`84611718`, a `2v1v1`) is stuck on this.

**Player names.** Any player name arriving over the wire (body or query param) must be alias-resolved — clients send in-game aliases (`skp`→`Skip`). Don't call `resolve_player_name` ad-hoc in handlers; type the field as `api_types.PlayerName` (works in `list[PlayerName]` too) so resolution happens at validation and can't be forgotten. Internally, resolve with `resolve_player_name(name, player.color)` — color disambiguates the shared alias "pc" (purple→pcap, pink→Pancake).

**MatchDetails cache invalidation.** `cache.details_from_id` is an in-process LRU over the durable `match_details_cache` table; rows are stamped with `match_details.DETAILS_VERSION`. A `MatchDetails` *schema* change auto-bumps the version (embedded `model_json_schema()` hash); a *derivation logic* change that leaves the schema unchanged requires manually bumping `_DETAILS_LOGIC_VERSION` in `match_details.py` — otherwise stale rows keep being served. Reparse paths call `delete_cached_details(match_id)` (raw replay changed, version didn't). Browsers also cache `/api/details/` for 1h — hard-refresh (Ctrl-Shift-R) when verifying.

**`notify()`** (Discord webhook) is best-effort and swallows its own errors, but it's still a blocking HTTP call — in async code dispatch it via `asyncio.to_thread`.

**Backfill endpoint pattern.** Ops endpoints take `max_to_update: int`, loop incrementally, return `{"updated": N, ...}`, and are marked `include_in_schema=IS_DEV` (hidden from prod docs but still routable).

## Python conventions

- **This is Python 3.14 (`requires-python = ">=3.14"`, ruff `py314`, mypy 3.14).** Unparenthesized `except ValueError, TypeError:` is valid — [PEP 758](https://peps.python.org/pep-0758/) — and so is `except* A, B:`. `ruff format` actively rewrites the parenthesized form to it. That is correct, current code: do not "fix" it back, and never report it as a syntax error.
- **Exception: any `radarvan/` module reachable from `ml/` must stay parseable by Python 3.13**, because torch has no 3.14 wheel and training runs in `.venv-ml` (3.13) with the repo on `PYTHONPATH`. There, PEP 758's bare form *is* a SyntaxError — keep those `except` clauses parenthesized **and tagged `# fmt: skip`**, or `make format` silently rewrites them back and breaks training (`player_role.py` is the live example). Same constraint as the `from __future__ import annotations` at the top of `player_rating.py`. `tests/test_ml_venv_imports.py` catches a break wherever `.venv-ml` exists.
- **Never use `TYPE_CHECKING`** — resolve circular imports by moving code to a module that already has access to all needed types (e.g. `derived/` imports only `api_types` and `db_utils`, so `cache.py` and `player_rating.py` can both depend on it).
- **Never mutate function inputs** — return new values (`model_copy(update=...)` for Pydantic).
- camelCase wire aliases with `populate_by_name`. (Do not add `slots=True` to a `BaseModel`'s `ConfigDict` expecting a memory win — pydantic v2's `ConfigDict` has no such key for `BaseModel`; it's silently ignored. Real slots require `pydantic.dataclasses.dataclass(..., slots=True)`, which isn't compatible with `api_types.py`'s OpenAPI/TS-codegen role.)

## Domain gotchas

### Replay data model

- **`EnhancedReplayV2.stats` is optional** — old replays have `stats=None`. Always guard before touching `stats.*`; return empty structures in the `None` branch. `has_enhanced_stats` in the DB = `replay.stats is not None`.
- **Summary index vs header order are NOT the same.** `replay.summary[*].index` (1-based) is the canonical player index used by every `stats.*_events` field (`killEvents.killerPlayer`, `buildEvents.player`, …). `replay.header.metadata.players` is a *different order* and 0-based — never enumerate it to resolve event indices. Build `name_by_idx = {p.index: p.name for p in replay.summary}`.
- **Body chunk `details` is a plain dict with capitalized keys** — `{"Name": ..., "Cost": ...}`. Use `d.get("Name")`; `getattr` and lowercase keys silently return None. Guard with `details = chunk.details if isinstance(chunk.details, dict) else {}`.
- **Starting position**: replay `StartingPosition` is 0-based; map-data `player_number` is 1-based. The `+1` happens in `utils.players_from_replay()`.
- **Team 0 players are observers/disconnected**, not FFA participants; `categorize_game_type` ignores them.
- **Per-player money**: use `stats.players[*].moneySpent`/`moneyEarned` (surfaced as `MatchDetails.player_money_spent/collected`) — `PlayerSummary.MoneySpent` is always 0 for v2 replays.
- **Buildings vs units** are distinguished by `object_type`/`victim_type == "structure"` on build/kill events.
- **Game-night dates**: `utils.game_night_date` converts UTC to US Eastern with a 5am rollover so post-midnight games count toward the evening they started. Use it, not `.date()`.
- **APM has two paths** (`apm.py`): per-order `replay.body` chunks when present, else derived from stats events (newer cncstats outputs ship an empty body). Scoped to non-observer humans; `apm_over_time` returns 10s windows scaled to APM.

### Timelines and special powers (`timeline_events.py`)

- `body[].details.Name` for `SpecialPowerAt*` orders encodes three families: `SpecialAbility*` (unit abilities — skip, they flood timelines), `SpecialPower*` (generals-panel powers), `Superweapon*` (mix of powers AND true superweapons — a true launch matches `_SUPERWEAPON_ACTIVATION_KEYWORDS`). Superweapon *buildings* are detected by name against `_SUPERWEAPON_STRUCTURES`, not cost.
- `MatchDetails.timeline_events` markers: `search_and_destroy` fires only on 0→1 battle-plan flips; `low_power` only on OK→low transitions; rank-ups with `rank_level <= 1` or seed frames are dropped.
- Object names rendered to the UI go through `replay_helpers.clean_object_name` (strips `Lazr_`-style prefix then faction prefix); power names additionally through `clean_power_name`.

### Matches, overrides, reparse

- `matches_differ` compares map, winner, duration (2dp), incomplete, game_version, and the sorted player tuples — extend it if new fields must trigger refresh.
- `WinnerOverride` takes full precedence in `match_to_matchinfo` and is also baked into freshly parsed JSON by `parse_replay_data`; overrides survive reparses.
- `session.merge()` + `onupdate` columns: merge copies attribute state by PK, so an unset `updated_at`/`computed_at` merges as NULL. Always set such columns explicitly on objects passed to `merge()` (see `save_parsed_json`, `save_cached_details`).
- `list_jsons_parsed_before` uses PostgreSQL `DISTINCT ON (match_id)` and excludes match_ids with any record newer than the cutoff.
- The `match_compostion` table name misspelling is baked into an early migration — intentionally preserved everywhere; do not "fix" without a migration.

### Maps

- **Coordinates**: CnC uses bottom-left origin (y up); CSS top-left. Convert with `top = (1 - y / height) * 100%` (`Map.tsx`); same convention for `eventDots` overlays.
- **Name resolution**: user-supplied map names are matched case-/whitespace-insensitively — `ReplayManager.resolve_map_name(name)` returns the canonical stored name; `replay_files.map_key` is the normalized join key between `Match.map` paths and `MapData.map_name`. Image lookup is S3-only (`find_s3_webp`, tries variants) — the legacy bundled `public/maps`/`dist/maps` fallback was removed once every map name in real match data was confirmed to resolve via S3.
- **CRC**: `MapData.crc` is uppercase hex matching replay-header `mapCrc`. Played maps: derive from a sample match's parsed JSON (`missing_maps.crc_for_map`/`backfill_map_crcs`). Uploaded maps: recompute from raw bytes via `compute_map_crc` (SAGE rotate-left-1-then-add, validated against cncstats). cncstats uses decimal (`int(hex, 16)`). Pushing to cncstats (`/add_map`, headers `X-API-Key`/`X-Map-CRC`/`X-Map-File`) is gated on `CNCSTATS_API_KEY`, deduped via `MapData.cncstats_synced_at` + `/map_exists`, and run concurrently through `CncstatsClient`'s async methods.
- **OpenAPI generator path conflicts**: the generator silently merges a static route with a parameterized sibling sharing its prefix (e.g. `/api/map_data/by_player_count` vs `/api/map_data/{map_name}`). Give new static routes a distinct top-level path (`/api/bracket_eligible_players` exists for this reason).

### Bracket (1v1 double elimination)

- `bracket.py` is pure and hand-verified (loss accounting); the DB stores only seeds + per-match date/best-of/scores; players/winners/status are re-derived every call via `resolve_bracket`. Keep new bracket logic in `bracket.py` where it's unit-testable, not in the route.
- **Losers-bracket construction is organized by dependency *depth*, not winners-bracket round number** (see the module docstring and `_match_depths`) — depth is how many rounds of real (non-bye) competition had to finish before a match was playable; a Round-2 match between two bye seeds is depth 1 (as immediately available as Round 1), a Round-2 match against a Round-1 winner is depth 2. `build_topology` groups WB losers by depth and merges one depth-group at a time — never assume "WB round N's losers all enter the losers bracket in the same round." This shape was checked against a real Challonge-generated bracket, not derived from first principles alone.
- Every pairing decision (`_reduce_to`'s self-pairing, `_merge_droppers`' cross-merge) goes through `_pair_safely`, which searches for a collision-free ordering (mirror → rotations → full permutation) via `_would_rematch` rather than a hand-derived rotation offset. If you touch either function, don't reintroduce a fixed same-index pairing — `test_no_immediate_rematch` (parametrized across all 8 player counts) will catch a regression.
- `POST /api/bracket/{match_id}` has **PATCH semantics** via `model_fields_set` — omitted fields keep stored values, explicit null clears. Edits that would re-route players through an already-scored downstream match are rejected with 409 (`bracket.rerouted_scored_matches`); the admin must clear the downstream result first.

### Caching / scheduling specifics

- `_draft_cache` in `routes/draft.py` stays a manual TTLCache (allow-listed in `tests/test_derived_registry.py`) — not because the registry couldn't bind it, but because a draft is a *random* result held steady, not a value derived from the corpus: version-keying would re-randomize everyone's teams the moment a game landed.
- **`/api/balance_teams/` has two layers, on purpose.** `create_teams.balance_teams` is `@derived(on=CORPUS, maxsize=128)` (`games` binds the corpus, `player_list` is the key) and so tracks the ratings. The *route* (`routes/players.py`) then holds its answer for **6 hours per roster** in a plain `TTLCache`, keyed on the alias-resolved player set — so asking again with the same players during a game night returns the same teams even after games land. That hold is a product decision (the group is split on whether teams should reshuffle mid-night), which is why it lives at the route rather than in the derivation, and why it is a wall clock rather than a version token. Raw spellings are re-applied per request, so the hold does not freeze one caller's aliases onto another's response. Before this split, the 12h TTL sat on the derivation and silently served stale *ratings* — the same visible effect, but by accident of a cache key, and it made `/api/partition_teams/` (never held) disagree with it.
- Scheduler (`schedule.py`): scrape+register every 6h, superlatives recompute at 04:00, player profiles at 04:30; all take `db_manager` and are also triggerable via `POST /api/scrape/{days}` and `POST /api/superlatives/recompute`.
- **`compute_game_night_summary` at 11:00 is the only scheduled job that spends money**, and its time is load-bearing rather than cosmetic. `utils.game_night_date` rolls over at **5am US Eastern**, so 11:00 in the process timezone (UTC on Heroku) is the first slot at which last night is definitively closed in both EST and EDT. Running it with the 04:00 jobs would summarize an evening still being played — and the row is permanent, since nothing regenerates. It writes **at most one row per run** (the latest closed night, skipped if it already has one, skipped below `MIN_MATCHES_FOR_SUMMARY`), so deploying it does not backfill the archive and a missed run costs that night its recap rather than queueing several calls. A night with no row returns `ai_summary: null` and the page omits the section.

## Reference fixtures (`references/`)

`references/` holds real cncstats and API payloads for offline inspection — invoke the **`replay-fixtures`** skill when `MatchDetails` output looks wrong or you need a real `stats.*` event shape.

Docs elsewhere in the repo: `auth.md` (Discord OAuth setup), `SYNERGY_METHODOLOGY.md`, `ml/model_design.md`. `radarvan/api_types.py` is the source of truth for the wire format (the unused `proto/match.proto` was removed).
