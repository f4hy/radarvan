# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radarvan is a statistics tracking application for Command & Conquer: Generals Zero Hour. It consists of a React frontend and a FastAPI Python backend that scrapes game data, parses replay files, and provides various statistics endpoints.

## Common Commands

### Combined (Makefile)
The `Makefile` is the canonical entry point for formatting, linting, type-checking, and CI. `make help` lists every target.
- `make all` - Format + auto-fix lint + type-check across **both** Python and TypeScript (run this before pushing)
- `make check` - Python lint + mypy (no formatting)
- `make ts-check` - TS format-check + ESLint + tsc
- `make install` - `uv sync` + `npm install`
- `make test` - `uv run pytest`
- `make build` - Runs `check` + `ts-check`, then `uv build`
- `make ci` - Full pipeline: `clean install all build`
- Python-only targets: `format`, `lint`, `lint-fix`, `typecheck`. TS-only: `ts-format`, `ts-lint`, `ts-lint-fix`, `ts-typecheck`.

### Frontend (Vite + React)
- `npm start` - Start Vite dev server (`/api` proxied to localhost:8000 via `vite.config.ts`)
- `npm run build` - Type-check and build production bundle (`tsc && vite build`)
- `npm test` - Run vitest test suite

### Backend (Python/FastAPI)
- `fastapi run radarvan/main.py` - Start the server (matches `Procfile`)
- Python ≥3.13 required; deps locked in `uv.lock` (install via `make install` or `uv sync`)
- `alembic upgrade head` - Run migrations
- `DATABASE_URL` env var must be set; `DEV=1` disables scheduled scraping

### Code Generation
- `./gen_client.sh` - Regenerate TypeScript API client from the running FastAPI server's OpenAPI spec; FastAPI dev server must be running first
- OpenAPI client code is auto-generated in `src/api/` (DO NOT manually edit files marked with auto-generation warnings)
- `proto/match.proto` exists but is not used by the current code paths — `radarvan/api_types.py` (Pydantic) is the source of truth for the wire format

## Architecture

### Frontend Structure
- **Entry point**: `src/index.tsx` → `src/App.tsx` → `src/Menu.tsx`
- **Navigation**: Menu component provides drawer-based navigation between different views
- **Main views**:
  - Matches (match listings)
  - PlayerStats (individual player statistics)
  - GeneralStats (statistics by general/faction)
  - Draft (`src/Draft.tsx`) — map/player draft with randomized position and general assignment
  - DebugData (debug view, only shown with `?debug=True` query param)
- **API Client**: `src/Client.ts` configures the auto-generated API client, switching between localhost:8000 (dev) and production Heroku endpoint based on NODE_ENV
- **Styling**: Uses Material-UI (@mui/material) with responsive theming
- **Charting**: Uses recharts library for data visualization

### Backend Structure
- **Main app**: `radarvan/main.py` - FastAPI application with CORS middleware and request timing
- **Database**: SQLAlchemy ORM with PostgreSQL, managed via `db_utils.py` and `db.py`
- **Key modules**:
  - `matches.py` - Match listing, retrieval, conversion (`match_from_replay`, `replay_to_db_match`, `match_to_matchinfo`, `matches_differ`)
  - `match_details.py` - Detailed match statistics (APM, upgrades, spending over time, first blood, kill events with map coordinates)
  - `player_stats.py` - Player-specific win/loss stats by general; accepts `game_format` filter; counts all games per category
  - `general_stats.py` - General/faction-specific statistics
  - `superlatives.py` - Top-N leaderboard stats (streaks, APM, kills, money, etc.)
  - `draft.py` - Spatial clustering assignment for draft randomization; called by `POST /api/draft/randomize` (results cached 30 min via `TTLCache`)
  - `game_composition.py` - `categorize_game_type`, `competitive_game_filter`
  - `replay_files.py` - Replay file management; `parse_json(s3_uri)` loads JSON→EnhancedReplayV2 without re-running cncstats; `parse_replay` runs cncstats if JSON not cached
  - `scrape_games.py` - Web scraping to gather new game data
  - `parse_replay.py` - Replay file parsing (runs cncstats binary)
  - `schedule.py` - Scheduled tasks for scraping
  - `db_utils.py` - Database session management and replay repository (`ReplayManager`)
- **API types**: `radarvan/api_types.py` — Pydantic models that define every REST request/response shape (`MatchInfo`, `PlayerStat`, `MatchDetails`, `General`/`Team`/`Faction` enums, etc.). This is the canonical schema; TS types are generated from the resulting OpenAPI spec.
- **Replay model**: `radarvan/cncstats_model/zhreplay.py` defines `EnhancedReplayV2` (the parsed-replay shape from the cncstats binary). Use this; the older `cncstats_types_v2.py` shapes are reference-only.

### Data Flow
1. Game replays are collected (via scraping or manual upload)
2. Replays are parsed to extract match details (players, generals, teams, winner, costs, actions)
3. Data is stored in PostgreSQL database; the original `.rep` and the parsed JSON live in S3 (`s3://generals-stats/radarvan/dev/`)
4. FastAPI serves statistics via REST endpoints
5. React frontend fetches and displays data using auto-generated TypeScript client

### Key Patterns
- **Game format filtering**: `matches.filter_by_format(games, game_format)` filters by category string ("1v1", "2v2", etc.); `game_composition.competitive_game_filter` requires balanced, non-comp-stomp, team games
- **Player stats sources**: `sorted_deduped_matches` (all games, for counts) vs `competitive_matches` (filtered, for W/L) — `get_player_stats` receives all games and filters internally
- **Replay JSON loading**: Use `replay_files.parse_json(json_s3_uri)` to load an existing JSON from S3 without re-running cncstats; always set `replay.Header.FileName = replay_file_url` after loading
- **Canonical replay type**: All replay-handling code uses `EnhancedReplayV2` (from `cncstats_types_v2.py`), not `EnhancedReplay`. Do not import `EnhancedReplay` in new code.
- **Match comparison**: `matches.matches_differ(existing, new)` compares map, winner, duration, incomplete, game_version, and players (name, general, team, color, is_winner, starting_position)
- **Backfill endpoints**: POST endpoints with `max_to_update: int` param that loop through matches and update incrementally; return `{"updated": N}`

### Environment Configuration
- Frontend dev proxy is configured in `vite.config.ts` (only `/api` routes proxied to `localhost:8000`; static assets served directly from `public/`)
- Backend reads `DATABASE_URL` from environment variables
- `DEV` environment variable controls whether scheduled tasks run
- Production deployment is on Heroku (radarvan-5e9c302c60e6.herokuapp.com)
- Static files served via explicit `serve_index()` route (returns `index.html` with `Cache-Control: no-cache`) followed by `StaticFiles` mount — ensures browser revalidates after deploys

## Reference Fixtures (`references/`)

Use these to inspect real cncstats / API shapes without running anything. Read with `jq` (already installed).

- **`references/example_replay.rep`** — raw replay binary (match `92990953`). The unparsed input that cncstats consumes. Rarely needed directly; consult only if debugging the parser itself.
- **`references/example_cncstats_output.json`** — the parsed JSON cncstats emits from the `.rep` above. **This is the canonical shape of `EnhancedReplayV2`** as it arrives in our code. Consult whenever asking "what does a replay's `body` / `stats.buildEvents` / `summary` actually look like?" Has the corrected (non-empty) body with 9 597 chunks and the full `stats` block (build / kill / capture / battle-plan / energy / rank / science / skill / radar / death / time-series events).
- **`references/example_api_match_details.json`** — sample response from `GET /api/details/{match_id}` (match `349863312`). Consult when asking "what does the wire shape of `MatchDetails` look like to the front-end?" Note: this was captured *before* the upgradeName / new-event-types fixes, so its `upgradeEvents` field has empty strings — useful as a "stale cache" example, not as ground truth.
- **`references/cncstats_schema.json`** — the cncstats Swagger 2.0 spec. Definitions for every event type live under `definitions.*` (e.g. `zhreplay.EnrichedBuildEvent`, `statsfile.BattlePlanEvent`). Consult when asking "what fields are guaranteed on event X, and what's their type?"

Common workflow: when something in `MatchDetails` looks wrong, first `jq` the matching path in `example_cncstats_output.json` to confirm what cncstats produces, then trace through `radarvan/match_details.py` or `radarvan/apm.py` to find the transformation that's losing data. To exercise the full pipeline locally:

```python
import json
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.match_details import match_details_from_replay
replay = EnhancedReplayV2.model_validate(json.load(open("references/example_cncstats_output.json")))
details = match_details_from_replay(replay)
```

## Python Conventions

- **Never use `TYPE_CHECKING`** — resolve circular imports by moving code to a module that already has access to all needed types
- **`filter_by_format`** lives in `matches.py` (not `game_composition.py`) because it operates on `list[MatchInfo]`

## Gotchas

- **Map coordinates**: CnC Generals uses bottom-left origin (y increases upward); CSS uses top-left origin. In `Map.tsx`, convert with `top = (1 - y / height) * 100%`.
- **Starting position indexing**: Replay `StartingPosition` is 0-based; map data `player_number` is 1-based. The `+1` conversion is applied in `utils.players_from_replay()`.
- **OpenAPI generator path conflicts**: The generator silently merges routes that share a path prefix with a parameterized sibling (e.g., `/api/map_data/by_player_count` conflicts with `/api/map_data/{map_name}`). Use a distinct top-level path instead.
- **`GameMap` component**: The map display component is named `GameMap` (exported from `src/Map.tsx`) to avoid shadowing the JS `Map` constructor.
- **`game_composition.py` team 0**: Players on team 0 are observers or disconnected players, not FFA participants. `categorize_game_type` ignores them when determining game type.
- **Draft cache key**: `_draft_cache` in `main.py` uses manual dict-style `TTLCache` (not `@cached` decorator) because `replay_manager` is a FastAPI `Depends` parameter that can't pass through the decorator.
- **`EnhancedReplayV2.Stats` is optional**: Old-format replays have `Stats=None`. Always guard with `if replay.Stats is None` before accessing `Stats.players`, `Stats.timeSeries`, etc. Return empty data structures in the `None` branch.
- **v2 Stats player indices**: `Stats.players[*].index` and `Stats.timeSeries.players[*].index` are the same index space used in all event objects (`killEvents.killerPlayer`, `buildEvents.player`, etc.). Build `name_by_idx = {p.index: p.displayName for p in replay.Stats.players}` to resolve names.
- **`has_enhanced_stats` in DB**: Set via `replay.Stats is not None` (not by inspecting `BodyChunk.PlayerStats`, which no longer exists in v2).
- **`_is_building()` in `match_details.py`**: Currently always returns `False` — a placeholder until cncstats adds object-type metadata to kill/build events. The building stat buckets (`buildings_built`, `buildings_killed`, etc.) are intentionally scaffolded but always empty for now.
- **`MatchDetails.player_money_spent`**: Per-player end-of-game money spent (from `Stats.players[*].moneySpent`). Use this instead of `PlayerSummary.MoneySpent`, which is always 0 for v2 replays.
- **`MatchDetails.kill_events`**: List of `KillEventOutput` — each has `x`, `y` (game coordinates), `killerPlayer`/`victimPlayer` (display names), `killer`/`victim` (unit names), `damageType`, `atMinute`. Populated from `Stats.killEvents` with player indices resolved to names.
- **`MatchDetails.map_name`**: Map filename from `replay.Header.Metadata.MapFile`. Use this to display the `GameMap` component in match detail views.
- **`GameMap` event overlay**: Pass `eventDots?: EventDot[]` (from `src/Map.tsx`) to overlay dots on the map image. Coordinates use the same game-space system as all other map points — `left = (x / extent.width) * 100%`, `top = (1 - y / extent.height) * 100%`.
- **recharts Sankey `nodePadding`**: Applied uniformly to all columns — there is no per-column or per-node padding. The `node` and `link` props accept custom React elements that receive layout props (`x`, `y`, `width`, `height`, `payload`) injected by recharts. `payload.sourceLinks` is available to detect leaf nodes.
- **`session.merge()` and `onupdate`**: SQLAlchemy's `onupdate=func.now()` on a column only fires when SQLAlchemy emits an `UPDATE` for that column. `session.merge()` constructs a new Python object and merges by PK — if `updated_at` is not set on the object, merge overwrites the DB value with `NULL`. Always set `updated_at=datetime.utcnow()` explicitly on objects passed to `session.merge()` in `save_parsed_json`.
- **`list_jsons_parsed_before`**: Uses `DISTINCT ON (match_id)` (PostgreSQL) to return one `ParsedReplayJson` per match. Excludes any `match_id` that has a record with `coalesce(updated_at, created_at) >= before` via a `NOT IN` subquery, so only match_ids where all records predate the cutoff are returned.
- **Player color utilities**: `getColorHex(colorName)` and `buildPlayerColorMap(summaries, transform?)` are in `src/utils.ts`. Use these instead of inline `reduce` calls when mapping player names to colors. `buildPlayerColorMap` accepts an optional transform (e.g. `getColorHex`) for hex conversion.
- **Shared `WinRateRadar` component**: `src/WinRateRadar.tsx` renders a recharts RadarChart of win rates. Expects `data: { name: string; winRate: number }[]` and optional `aspect` prop. Used by both `PlayerStats.tsx` and `GeneralStats.tsx`.
- **Map name resolution**: User-supplied map names should be looked up case- and whitespace-insensitively. Use `ReplayManager.resolve_map_name(name)` to get the canonical stored name, then call `get_map_data`/image helpers with that. `missing_maps.find_s3_webp` also tries case- and whitespace-stripped variants in S3.
- **Local map image fallback**: `_load_map_image_bytes` in `main.py` first tries S3 via `find_s3_webp`, then exact `dist/maps/{name}.webp`, then a normalized-substring scan of `dist/maps/` (filenames there have prefixes like `maps_defcon6_defcon6.webp` that include the map name as a substring).
- **`MapRenderPlayer` request shape**: `POST /api/map_render` takes a map name and a list of `MapRenderPlayer` (name, general, team, position_number) and returns a PNG with overlays burned in. Uses `radarvan/map_render.py` (Pillow); team colors mirror frontend `TEAM_COLORS` in `Draft.tsx`.
- **APM derivation has two paths**: `radarvan/apm.py` prefers `replay.body` (legacy per-order chunks) and falls back to `replay.stats.*_events` (build / capture / battle-plan / science-points) when the body is empty — newer cncstats outputs sometimes ship an empty body. `apm_over_time(replay)` returns `{minute: {player_name: apm}}` in 1-minute windows. Counts are scoped to non-observer humans (`team >= 0`, `player_type == "Human"`); active duration is first-to-last action frame with a total-duration fallback.
- **Body chunk `details` is a plain dict with capitalized keys**: `BodyChunk.details: Any` deserializes to e.g. `{"Name": "Upgrade_InfantryCaptureBuilding", "Cost": 1000}` — `getattr(d, "Name", None)` always returns `None` (it's not an object), and `d.get("name")` misses (case-sensitive). Always use `d.get("Name")` / `d.get("Cost")`. The pattern `details = chunk.details if isinstance(chunk.details, dict) else {}` is in `events_from_replay`.
- **Summary index vs header order are NOT the same**: `replay.summary[*].index` (1-based) is the canonical player index used in every `stats.*_events.player` / `killEvents.killerPlayer` / `buildEvents.player` / `battle_plan_events.player` / etc. `replay.header.metadata.players[*]` is in a *different order* and is 0-based — don't enumerate that list to resolve event player indices. Build `name_by_idx = {p.index: p.name for p in replay.summary}`.
- **`details_from_id` is a process-wide LRU cache**: `radarvan/cache.py:details_from_id` memoises `MatchDetails` by `match_id` until the process restarts or `invalidate_match_caches()` runs. After changing any code that affects `MatchDetails` output, either restart FastAPI or `POST /api/reparse/{match_id}` to invalidate. Browsers also cache `/api/details/` for 1 hour (`Cache-Control: private, max-age=3600`) — hard-refresh (Ctrl-Shift-R) when verifying changes.
- **Object-name cleaning**: `radarvan/match_details.py:_clean_object_name` strips a leading `<Prefix>_` token (e.g. `Lazr_`, `Tank_`, `SupW_`) **and then** the `China` / `America` / `GLA` faction prefix — so `Lazr_AmericaVehicleChinook` → `VehicleChinook`. Use it for build / upgrade / superweapon names rendered to the UI. `_clean_power_name` additionally strips `SpecialAbility` / `SpecialPower` / `Superweapon` prefixes for power names.
- **Special-power categorization**: cncstats encodes three families inside `body[].details.Name` for `SpecialPowerAtLocation` / `SpecialPowerAtObject` orders: (a) `SpecialAbility*` — unit-level abilities (capture-building, laser-guided missile, etc.) — skip these on timelines, they flood the data; (b) `SpecialPower*` — actual generals-panel powers (SpyDrone, SpySatellite, …); (c) `Superweapon*` — a mix of generals powers AND true base-bound superweapons. To distinguish a true superweapon activation, match the name against `_SUPERWEAPON_ACTIVATION_KEYWORDS` (`NeutronMissile`, `NuclearMissile`, `ParticleCannon`, `ScudStorm`, `EMPPulse`, `AnthraxBomb`, `SpectreGunship`). Anything else under `Superweapon*` is treated as a generals power.
- **Superweapon buildings**: detected by substring match on the cleaned object name against `_SUPERWEAPON_STRUCTURES` (`NuclearMissileLauncher`, `ParticleCannonUplink`, `ScudStorm`). Cost is typically 5 000 but cost-based detection is brittle — stick to the name list.
- **`MatchDetails.timeline_events`**: a flat `list[TimelineEvent]` (each has `player_name`, `at_minute`, `event_name`, `event_type`, `cost`) of player-driven markers — `upgrade`, `rank_up`, `generals_power`, `superweapon_built`, `superweapon_activated`, `search_and_destroy`, `low_power`. `search_and_destroy` fires only on `0 → 1` transitions of `battle_plan_events.search_and_destroy`. `low_power` fires only on the OK → low transition (`consumption > production` from `energy_events`). Rank-up events with `rank_level <= 1` or `frame <= 0` are dropped (they're the initial state).
- **EventChart is fully MUI**: `src/ShowMatchDetails.tsx:EventChart` renders the timeline using `@mui/material` `Box`/`Stack`/`Paper`/`Tooltip` + `@mui/icons-material` icons — no recharts. Lanes are grouped by player; rows for a single player are kept together via the explicit `ROW_ORDER` array. Adding a new event type means updating `EVENT_TYPE_META`, `EVENT_TYPE_ICON`, and (if a new row) `ROW_ORDER` together.

## Key Technical Details

- **TypeScript**: Strict mode enabled, targeting ES6
- **Auto-generated code**: Files in `src/api/` are generated from OpenAPI spec - don't edit manually
- **Protobuf usage**: Match data structures are defined in proto files and compiled to TypeScript
- **Database migrations**: Managed with Alembic (config in `alembic.ini`)
- **Cloud integration**: Replay files and parsed JSON are stored in S3 (`s3://generals-stats/radarvan/dev/`) via `fsspec`; local filesystem is not used for replays
- **Player name resolution**: `resolve_player_name(name, color)` handles name aliases/overrides; used in player stats and superlatives
- **Frontend format toggles**: `FORMAT_OPTIONS` arrays drive ToggleButtonGroup; selected format is passed as `gameFormat` query param; state is reset on format change
