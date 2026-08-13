# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radarvan is a statistics tracker for Command & Conquer: Generals Zero Hour. A FastAPI backend scrapes/accepts game replays, parses them via the external cncstats service, stores results in PostgreSQL + S3, and serves stats; a React frontend renders them. Production runs on Heroku (radarvan-5e9c302c60e6.herokuapp.com).

## Commands

The `Makefile` is the canonical entry point; `make help` lists every target.

- `make all` — format + auto-fix lint + type-check **both** Python and TypeScript (run before pushing)
- `make check` — Python ruff + mypy (no formatting) · `make ts-check` — TS format-check + Biome lint + tsc
- `make test` — `uv run pytest` (tests in `tests/`, fixture JSONs live there too)
- `make install` — `uv sync` + `npm install` · `make ci` — `clean install all build`
- Python-only: `format`, `lint`, `lint-fix`, `typecheck` · TS-only: `ts-format`, `ts-lint`, `ts-lint-fix`, `ts-typecheck`

**Frontend**: `npm start` (Vite dev server; only `/api` is proxied to localhost:8000 via `vite.config.ts`), `npm run build`, `npm test` (vitest).

**Backend**: `fastapi run radarvan/main.py` (matches `Procfile`). Python ≥3.14, deps locked in `uv.lock`. `alembic upgrade head` for migrations (config in `alembic.ini`).

**Client codegen**: `./gen_client.sh` regenerates the TypeScript client in `src/api/` from the running server's OpenAPI spec — the FastAPI server must already be running and serving your changed code. Always use this script (not `npm run openapi-ts` or a manual generator invocation). Never hand-edit `src/api/` (auto-generated). `PlayerEnum.ts` reorders on every regen (Python set iteration) — that churn is normal.

### Dev workflow

- The dev servers are **already running** in the user's own terminals: Vite on 5173 (proxying `/api`), FastAPI on 8000 (auto-reloads on edit). Never launch your own instances to verify changes — connect to the running ones (confirm with `curl`/`ss -ltnp` if unsure). Never run broad `pkill -f vite` / `pkill -f fastapi`; if a stray process must be killed, target the exact PID.
- Do not commit or push (and don't ask to) unless explicitly told. Finish the work, report what changed, and leave it in the working tree — the user manages commits.
- **Fetching real data (a match, replay, player stats, etc.) to inspect or verify something: use the running API at `http://localhost:8000` (`curl`), not a direct DB/S3 connection.** The service is always running; it's the intended read path and matches what the frontend actually sees. Reserve direct `DatabaseManager`/`replay_files` scripting for cases the API genuinely can't express.
- **When exploring code, read the source file directly (`Read` tool) rather than chaining several `grep`/`sed`/`awk` shell commands.** Use `grep`/`Bash` only for repo-wide searches (finding *where* something is defined/used across many files) — once you know the file, read it.
- **Playwright (MCP tool or `e2e/` tests) must use Firefox — never Chrome/Chromium.** Pass the Firefox browser/channel explicitly wherever the driver defaults to Chromium. The bundled Playwright MCP server here defaults to a Chromium build (`chrome` channel) that isn't installed on this host, so it errors out on launch — drive Firefox directly instead (`const { firefox } = require('@playwright/test')` from the project root, so `node_modules` resolves).
- **Easiest way to inspect one specific match (including its map render) is the DebugData page**, not the Matches list: `http://localhost:5173/?page=debug-data`, then enter the match ID in the `matchId` field and submit — it works via direct URL even though the sidebar link itself is admin-gated (`status.user.is_admin`), and it sidesteps the Matches page's `exclude_dev=true` filtering (which hides `is_dev` matches — e.g. locally-uploaded test replays — unless you're logged in as admin).
- **`GET /api/map_data/{map_name}` responses are cached by the browser for 24h** (`Cache-Control: private, max-age=86400`, set in `routes/maps.py`). After reparsing/changing a map's stored geometry, a normal reload won't show the update in a browser that already fetched it — hard-refresh (Ctrl-Shift-R) to bypass the cache.
- **Never call `GET /api/matchup_commentary/` (or anything that reaches `matchup_commentary.generate_commentary`) without asking first — it is a GET, but a cache *miss* still generates. — it spends real tokens/money on every call, against whichever provider `COMMENTARY_PROVIDER` currently selects (Anthropic or Gemini).** Each individual call needs its own explicit confirmation from the user; a prior "yes" doesn't cover the next one. Use the free `GET /api/matchup_commentary/prompt_preview` instead for anything about prompt content/size/structure — it builds the exact same payload without calling either provider.

### Environment variables

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Postgres (required; `postgres://` auto-rewritten to `postgresql://`) |
| `DEV` | Set = dev mode: no scheduler, ops routes visible in OpenAPI |
| `API_KEY_NORMAL` / `API_KEY_ADMIN` | Comma-separated keys for `X-API-Key`, by privilege tier (admin implies normal); `ENFORCE_AUTH` set = actually reject. The old `API_KEY_READ`/`API_KEY_WRITE` names still work as a fallback |
| `SESSION_SECRET` | Signs the session cookie (random per-process fallback in dev) |
| `DISCORD_CLIENT_ID/SECRET`, `DISCORD_REDIRECT_URI` | Discord OAuth login (see `auth.md`) |
| `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_VOICE_CHANNEL_ID` | Bot creds for syncing bracket match schedules to Discord Guild Scheduled Events (`discord_events.py`); all three required or it's a no-op |
| `NOTIFY_WEB_HOOK` | Discord webhook for `notify()` |
| `CNCSTATS_APIKEY` | Bearer token for cncstats **replay parsing** (`POST /replay`) |
| `CNCSTATS_API_KEY` | X-API-Key for the cncstats **map registry** (`/add_map`) — distinct from the above, do not conflate |
| `ML_ENSEMBLE_DIR`, `WINPROB_MODEL_PATH`/`WINPROB_STATS_PATH` | ONNX model files; endpoints 503 when absent. `ML_ENSEMBLE_DIR` (default `ml_ensemble`) holds an N-model win-prediction ensemble (`model-*.onnx` + shared `vocab.json`) - every prediction runs all N and reports mean + std (`ml.bootstrap_matrix`) |
| `RATE_LIMIT_PER_MINUTE` | Per-client sliding window on `/api` (0 disables) |
| `CLAUDE_API_KEY` / `GEMINI_API_KEY` | Matchup commentary LLM providers (`commentary/anthropic_client.py` / `commentary/gemini_client.py`); `commentary_available()` 503s when the active one's key is absent |
| `COMMENTARY_PROVIDER` | `"anthropic"` or `"gemini"` — which provider generates commentary; defaults to `"gemini"` (see `matchup_commentary.py`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP HTTP collector URL; tracing (`tracing.py`) is a no-op unless set |
| `OTEL_EXPORTER_OTLP_HEADERS` / `OTEL_SERVICE_NAME` | Optional auth headers for the OTLP backend / span service name (default `radarvan`) |

## Architecture

### Backend layout (`radarvan/`)

- **`main.py`** — app composition only: middleware order, router registration, lifespan (scheduler + cache warm), the single global exception handler, static serving. Route handlers live in **`routes/`** (admin, auth, bracket, draft, ffa, files, generals, map_upload, maps, matches, players, predict, superlatives, teams, tournaments, votes).
- **`db.py`** — SQLAlchemy ORM models. **`repositories/`** — per-entity repos over a `Session` (`BaseRepo` gives `auto_commit`/`notify`). **`db_utils.py`** — `DatabaseManager` (engine + sessionmaker + `get_replay_manager()` ctx manager) and `ReplayManager`, a multiple-inheritance facade over the repos; new code should prefer the specific repo, the facade exists for legacy callers.
- **`dependencies.py`** — DI singletons (`db_manager`, `IS_DEV`) and Depends providers: `get_db_session` (commit/rollback/close per request), `get_replay_manager`, `verify_api_key`/`require_admin_key` (+ the `ADMIN_ONLY` tag list), `get_current_user`/`require_current_user` (session cookie), `cache_short` (60s private cache header).
- **`api_types.py`** — Pydantic models defining every REST request/response shape. **This is the canonical wire schema**; TS types are generated from the resulting OpenAPI spec. Includes `PlayerName` (alias-resolving annotated str) and the `General`/`Team`/`Faction` enums.
- **`cncstats_model/zhreplay.py`** — `EnhancedReplayV2`, the parsed-replay shape from cncstats. This is the **only** replay type to import; `cncstats_types.py`/`cncstats_types_v2.py` are unused reference copies.
- Ingestion: **`scrape_games.py`** (gentool scraping) → **`replay_files.py`** (S3 read/write, `parse_replay`/`parse_json`/`reparse_paths`/`upload_and_parse`, presigned URLs) → **`parse_replay.py`** (calls cncstats, 1v1 team reassignment, winner overrides) → **`matches.py`** (`match_from_replay`, `replay_to_db_match`, `match_to_matchinfo`, `register_matches`, `reparse_*`, `matches_differ`, `filter_by_format`/`filter_since`/`filter_by_months_back`).
- Match details: **`match_details.py`** orchestrates the `/api/details/{id}` shape from per-concern extractors — **`apm.py`**, **`stats_extraction.py`** (time series + first blood), **`build_order.py`**, **`timeline_events.py`** — and owns the versioned details cache loaders (`load_match_details`, thread-safe `load_many_match_details`). **`replay_helpers.py`** has `clean_object_name` etc.
- Stats over `list[MatchInfo]`: `player_stats.py`, `general_stats.py`, `team_stats.py`, `map_stats.py`, `ffa_stats.py`, `head_to_head.py`, `superlatives.py` (records; persisted via `StatsRepo`), `game_composition.py` (`categorize_game_type`, `competitive_game_filter`).
- Ratings: **`player_rating.py`** (OpenSkill/PlackettLuce, upsets, daily deltas), **`player_skill.py`** (Whole-History Rating), **`player_synergy.py`** (ridge logistic; see `SYNERGY_METHODOLOGY.md`), **`create_teams.py`** (balanced team search).
- Tournaments: **`tournament.py`** (hard-coded round-robin team tournaments + reports) vs **`bracket.py`** (1v1 double-elim: pure topology generation + resolution for 9–16 entrants; DB stores only seeds + per-match scores, everything else is derived each call).
- Maps: **`missing_maps.py`** (fetch from cncstats, CRC, S3 assets, push registry), **`map_upload.py`** (user uploads), **`map_render.py`** (Pillow overlay PNG), **`map_choice.py`** + **`draft.py`** (weighted draw, position/general randomization).
- ML: **`ml_inference.py`** (pre-game win prediction; encoder in `ml/`) and **`winprob_inference.py`** (win-prob-over-time; encoder in `ml_win_prediction_over_time/`) — ONNX Runtime only, no torch in prod.
- Infra: **`cache.py`** (process-global caches + warming, see invariants), **`schedule.py`** (APScheduler jobs), **`cncstats_client.py`** (single httpx client for cncstats), **`middleware.py`**/`rate_limit.py` (request-id, rate limit), **`notify.py`** (best-effort Discord webhook; never raises), **`player_ids.py`** (identity tables, admin sets), **`utils.py`** (replay helpers, `game_night_date`, `locked_cached`), **`tracing.py`** (OpenTelemetry: OTLP HTTP export + FastAPI/httpx auto-instrumentation, no-op without `OTEL_EXPORTER_OTLP_ENDPOINT`).

### Auth model (three tiers)

1. Most `/api` routers require `X-API-Key` (`verify_api_key`), which accepts **either tier** — the HTTP method is irrelevant. A route needing the **admin** tier opts in explicitly with `dependencies=ADMIN_ONLY` (i.e. `Depends(require_admin_key)`): reparse, backfill, override, delete, scrape, recompute, map registry pushes. Normal tier covers everything the app itself does, including `POST /api/upload_replay`, draft randomization, and prediction. Only enforced when `ENFORCE_AUTH` is set; with no keys configured at all, auth is off. `has_admin_access` is the boolean form, for a normal-tier route with an admin-only *option* (commentary's `force_refresh`). `tests/test_auth_tiers.py` fails if a new mutating route picks neither tier.
2. Cookie-session routes (Discord OAuth): `routes/auth.py`, `votes.py`, `map_upload.py`, `bracket.py` writes, `admin.session_router` — deliberately **not** behind the API key; identity via signed session cookie. Admin checks: `player_ids.ADMIN_PLAYERS` (general admin) vs `player_ids.TOURNAMENT_ADMINS` (bracket only) — separate sets on purpose. An admin action the **UI** drives goes here, tagged `dependencies=ADMIN_LOGIN` (`require_admin_login`), *not* on the API-key router: the frontend ships one key to every visitor, so it can only ever be normal-tier. `POST /api/reparse/{match_id}` (the DebugData button, via `src/adminApi.ts`) is the example. `require_admin_login` also accepts an admin-tier key so curl/ops still work, and reads that header off the request instead of declaring it as a `Security` param — declaring it would wrongly advertise APIKeyHeader as the route's security scheme in the OpenAPI spec.
3. `maps.public_router` (map images) — no auth, because browsers load them via `<img src>`.

### Data flow

1. Replays arrive by scheduled gentool scrape or `POST /api/upload_replay`.
2. cncstats parses the `.rep`; the `.rep` and parsed JSON go to S3 (`s3://generals-stats/radarvan/dev/`), rows to Postgres (`ReplayFile` → `ParsedReplayJson` → `Match`+`MatchPlayer`+`MatchCompostion`).
3. Derived data is cached (in-process + `match_details_cache` table) and served via REST; the React app consumes it through the generated client.

### Frontend layout (`src/`)

- Entry `index.tsx` → `App.tsx` → `Menu.tsx` (drawer navigation). Views map ~1:1 to backend areas: `Matches`, `ShowMatchDetails`, `PlayerStats`, `PlayerRatings`, `PlayerSynergy`, `GeneralStats`, `MapStats`, `TeamStats`, `HeadToHead`, `FFA`, `Superlatives`, `Tournaments`, `Bracket`, `Draft`, `ChooseMap`/`MapVoting`, `MapUpload`, `BalanceTeams`, `AIPredictions`, `ReplayPlayback`, `Account`; `DebugData` only with `?debug=True`.
- `Client.ts` configures the generated client (localhost:8000 in dev, Heroku in prod). MUI for components, recharts for charts. The generated client points at an **absolute** base URL, so it never sends the session cookie (cross-origin in dev) — anything cookie-authenticated uses a relative `fetch(..., {credentials: "same-origin"})` through the Vite proxy instead: `auth.ts`, `bracketApi.ts`, `voting.ts`, `mapUpload.ts`, `adminApi.ts`.
- Shared pieces: `Map.tsx` (exports `GameMap`), `WinRateRadar.tsx`, `PlayerChip`, `utils.ts` (`getColorHex`, `buildPlayerColorMap`), `AuthContext`, `useErrorSnackbar`.

## Core invariants — read before writing backend code

**DB sessions and threads.** The request-scoped session comes from `Depends(get_replay_manager)`. Anything that outlives the request must open its own session via `db_manager.get_replay_manager()` (context manager): FastAPI runs background tasks *after* yield-dependency teardown, and scheduler jobs each open a fresh session per run (a shared long-lived session poisons every later job after one failed transaction). Never let session-bound ORM objects cross into `asyncio.to_thread` workers — extract plain values first (see `matches.ReparseInputs`) or use the per-thread loaders `match_details.load_many_match_details` / `superlatives.load_many_superlative_data`. When catching DB errors inside a loop and continuing, call `session.rollback()` in the except branch or every subsequent statement fails with `PendingRollbackError` (see `matches.register_matches`).

**`update_match` needs a detached Match.** `MatchRepo.update_match` clears `existing.players` then merges. Only ever pass it a fresh Match built by `replay_to_db_match` — passing a session-attached instance is the same object via the identity map, and the clear + delete-orphan cascade permanently deletes the match's players.

**Event loop.** Async handlers and scheduler jobs must push blocking work (cncstats HTTP, S3 I/O, heavy computation) through `asyncio.to_thread`. Sequential `to_thread` calls may share one session; concurrent ones must not.

**Caches.** cachetools caches are not thread-safe and sync endpoints run in uvicorn's threadpool: every process-global cache must be locked. For new caches use `utils.locked_cached(cache=..., key=...)`; the caches in `cache.py` keep explicit locks because they coordinate `cache_clear()`. Call `cache.invalidate_match_caches()` after anything that changes match data (registers, reparses, overrides, resets) — it clears all match caches and triggers a background re-warm on the single warm thread.

**The two match sets.** `cache.sorted_deduped_matches` = all games (use for counts/listings); `cache.competitive_matches` = complete + `competitive_game_filter` (balanced, non-comp-stomp, team game, ≤1 CPU) + every team has a known player (use for W/L, ratings, records). Both are keyed on `latest_match_ts` so they refresh when new matches land. `filter_by_format` lives in `matches.py` (it operates on `list[MatchInfo]`), not `game_composition.py`.

**Player roles — never re-derive them.** Whether a slot is a human, an AI, or a spectator comes from the replay header (`type == "C"` for AI; a spectator is a type-`"H"` slot with `playerTemplate` `-2`) and is persisted as `match_players.role` (`player_role.PlayerRole`). There is exactly **one** way to ask, and adding a second is a bug: build a `game_composition.MatchRoster` and read its partitions.

- `MatchInfo.roster()` — from a match (the common case; build once per match, it materializes everything up front)
- `MatchRoster.from_db_players(rows)` — from `match_players`
- `MatchRoster.from_header_players(header.metadata.players)` — at parse time, before anything is in the DB

Partitions: `.observers`, `.competitors` (played; teamless slots included), `.participants` (competitors with `team > 0`), `.humans`, `.cpus`, `.human_participants`, `.teams`. `RosterSlot.has_known_general` is separate on purpose — that's parse quality, not role, and conflating the two is what the old `is_real()` did.

Do **not** write `p.team > 0`, `p.team == Team.OBSERVER`, or a name check against a CPU list at a call site. The codebase previously spelled the observer test three inconsistent ways and carried four disagreeing CPU detectors; AI slots named outside a five-entry list (Tactical AI, EasyArmy, MediumArmy) were counted as humans in 417 matches, which put comp-stomps on the competitive leaderboards. Guessing from the player's *name* survives only as `player_role.resolve_role`'s fallback for un-backfilled rows — the header is authoritative, and an AI's header name is empty. `role` is still nullable; tighten to NOT NULL once `list_matches_with_unset_roles` returns empty (blocked on one match — see the `Team` enum note below).

**`Team` stops at `FOUR`.** `utils.determine_team` raises `ValueError: 5 is not a valid Team` for any replay with 4+ teams, so such a match can't be parsed or reparsed. The header carries 8 slots, so a full FFA needs `Team` up to `EIGHT`. One known match (`84611718`, a `2v1v1`) is stuck on this.

**Player names.** Any player name arriving over the wire (body or query param) must be alias-resolved — clients send in-game aliases (`skp`→`Skip`). Don't call `resolve_player_name` ad-hoc in handlers; type the field as `api_types.PlayerName` (works in `list[PlayerName]` too) so resolution happens at validation and can't be forgotten. Internally, resolve with `resolve_player_name(name, player.color)` — color disambiguates the shared alias "pc" (purple→pcap, pink→Pancake).

**MatchDetails cache invalidation.** `cache.details_from_id` is an in-process LRU over the durable `match_details_cache` table; rows are stamped with `match_details.DETAILS_VERSION`. A `MatchDetails` *schema* change auto-bumps the version (embedded `model_json_schema()` hash); a *derivation logic* change that leaves the schema unchanged requires manually bumping `_DETAILS_LOGIC_VERSION` in `match_details.py` — otherwise stale rows keep being served. Reparse paths call `delete_cached_details(match_id)` (raw replay changed, version didn't). Browsers also cache `/api/details/` for 1h — hard-refresh (Ctrl-Shift-R) when verifying.

**`notify()`** (Discord webhook) is best-effort and swallows its own errors, but it's still a blocking HTTP call — in async code dispatch it via `asyncio.to_thread`.

**Backfill endpoint pattern.** Ops endpoints take `max_to_update: int`, loop incrementally, return `{"updated": N, ...}`, and are marked `include_in_schema=IS_DEV` (hidden from prod docs but still routable).

## Python conventions

- **Never use `TYPE_CHECKING`** — resolve circular imports by moving code to a module that already has access to all needed types (e.g. `locked_cached` lives in `utils.py` because `cache.py` imports `player_rating`).
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

- `_draft_cache` in `routes/draft.py` uses a manual dict-style TTLCache (not `@cached`) because `replay_manager` is a Depends parameter that can't pass through the decorator key.
- `balance_teams` is TTL-cached on the player set only (12h) — ratings staleness there is accepted.
- Scheduler (`schedule.py`): scrape+register every 6h, superlatives recompute at 04:00; both take `db_manager` and are also triggerable via `POST /api/scrape/{days}` and `POST /api/superlatives/recompute`.

### Frontend

- The map component is named `GameMap` (from `src/Map.tsx`) to avoid shadowing the JS `Map` constructor. Pass `eventDots?: EventDot[]` to overlay dots in game-space coordinates.
- `ShowMatchDetails.tsx:EventChart` is pure MUI (no recharts); event types are driven by one `EVENT_TYPES` array (label, row, icon) — `EVENT_TYPE_BY_KEY` and `ROW_ORDER` are both derived from it, so adding an event type only means adding an entry there.
- recharts Sankey `nodePadding` is uniform across columns; `node`/`link` accept custom elements receiving layout props; `payload.sourceLinks` detects leaf nodes.
- Use `getColorHex`/`buildPlayerColorMap` from `src/utils.ts` for player-color maps; `WinRateRadar` is the shared radar chart (`data: {name, winRate}[]`).
- Format toggles: `FORMAT_OPTIONS` arrays drive ToggleButtonGroups; selected format goes up as the `gameFormat` query param; reset dependent state on format change.
- Static serving: `serve_index()` returns `index.html` with `Cache-Control: no-cache` (so deploys revalidate), then a `StaticFiles` mount.
- `Bracket.tsx`'s `shortMatchLabel`/`ROUND_CODE` maps backend `round_name` strings (e.g. `"Winners Semifinal"`) to short card labels (`WSF-a`) — adding or renaming a round name in `bracket.py` (or a new `bracket_type`) needs a matching `ROUND_CODE` entry or it silently falls back to the raw name. `matchesById` and the hover-to-show-connector-lines callback are read via `useBracketData()` (`BracketDataContext`, mirroring `PlayerColorsContext`'s pattern) rather than threaded as props through `BracketNodeView`/`BracketTreeSection`/`LosersBracketColumns` — read from context in `MatchBox`, don't re-add prop drilling for a new cross-cutting concern there.

## Reference fixtures (`references/`)

Use these to inspect real cncstats / API shapes without running anything (`jq` is installed).

- **`example_replay.rep`** — raw replay binary (match `92990953`); only needed when debugging the parser itself.
- **`example_cncstats_output.json`** — the parsed JSON cncstats emits for that replay. **Canonical `EnhancedReplayV2` shape**: full body (9,597 chunks) and complete `stats` block (build/kill/capture/battle-plan/energy/rank/science/skill/radar/death/time-series events). First stop for "what does `stats.buildEvents` actually look like?"
- **`example_api_match_details.json`** — sample `GET /api/details/{id}` response (match `349863312`). Captured before the upgradeName fixes, so `upgradeEvents` has empty strings — useful as a stale-cache example, not ground truth.
- **`cncstats_schema.json`** — cncstats Swagger spec; per-event field guarantees live under `definitions.*`.

Workflow: when `MatchDetails` output looks wrong, first `jq` the matching path in `example_cncstats_output.json` to confirm what cncstats produces, then trace the transformation in `radarvan/match_details.py` (or the extractor it delegates to). Full local pipeline:

```python
import json
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.match_details import match_details_from_replay
replay = EnhancedReplayV2.model_validate(json.load(open("references/example_cncstats_output.json")))
details = match_details_from_replay(replay)
```

Docs elsewhere in the repo: `auth.md` (Discord OAuth setup), `SYNERGY_METHODOLOGY.md`, `ml/model_design.md`. `radarvan/api_types.py` is the source of truth for the wire format (the unused `proto/match.proto` was removed).
