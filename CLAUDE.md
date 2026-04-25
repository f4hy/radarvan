# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radarvan is a statistics tracking application for Command & Conquer: Generals Zero Hour. It consists of a React frontend and a FastAPI Python backend that scrapes game data, parses replay files, and provides various statistics endpoints.

## Common Commands

### Frontend (React)
- `npm start` - Start development server (proxies `/api` to localhost:8000 via `src/setupProxy.js`)
- `npm run build` - Build production bundle
- `npm test` - Run tests
- `prettier --write .` - Format code (configured to omit semicolons)

### Backend (Python/FastAPI)
The backend lives in the `radarvan/` directory. Common tasks typically involve:
- Starting the FastAPI server (check for uvicorn or similar in deployment scripts)
- Running database migrations with alembic: `alembic upgrade head`
- Database connection string is read from `DATABASE_URL` environment variable

### Code Generation
- `./gen_client.sh` - Regenerate TypeScript API client from the running FastAPI server's OpenAPI spec; FastAPI dev server must be running
- Protocol buffers are used for data structures (see `proto/match.proto`)
- TypeScript types are generated in `src/proto/match.ts` from the proto definitions
- OpenAPI client code is auto-generated in `src/api/` (DO NOT manually edit files marked with auto-generation warnings)

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
- **Data models**: Defined using Protocol Buffers in `proto/match.proto`, which defines:
  - Generals (USA, China, GLA factions and their variants)
  - Match information (players, teams, map, duration, winner)
  - Statistics (win/loss records, APM, costs, upgrades, spending over time)
- **API types**: `radarvan/api_types.py` — Pydantic models for REST responses (`MatchInfo`, `PlayerStat`, `PlayerStats`, `MatchDetails`, etc.)

### Data Flow
1. Game replays are collected (via scraping or manual upload)
2. Replays are parsed to extract match details (players, generals, teams, winner, costs, actions)
3. Data is stored in PostgreSQL database
4. FastAPI serves statistics via REST endpoints
5. React frontend fetches and displays data using auto-generated TypeScript client
6. Protocol buffers ensure type consistency between frontend and backend data structures

### Key Patterns
- **Game format filtering**: `matches.filter_by_format(games, game_format)` filters by category string ("1v1", "2v2", etc.); `game_composition.competitive_game_filter` requires balanced, non-comp-stomp, team games
- **Player stats sources**: `sorted_deduped_matches` (all games, for counts) vs `competitive_matches` (filtered, for W/L) — `get_player_stats` receives all games and filters internally
- **Replay JSON loading**: Use `replay_files.parse_json(json_s3_uri)` to load an existing JSON from S3 without re-running cncstats; always set `replay.Header.FileName = replay_file_url` after loading
- **Canonical replay type**: All replay-handling code uses `EnhancedReplayV2` (from `cncstats_types_v2.py`), not `EnhancedReplay`. Do not import `EnhancedReplay` in new code.
- **Match comparison**: `matches.matches_differ(existing, new)` compares map, winner, duration, incomplete, game_version, and players (name, general, team, color, is_winner, starting_position)
- **Backfill endpoints**: POST endpoints with `max_to_update: int` param that loop through matches and update incrementally; return `{"updated": N}`

### Environment Configuration
- Frontend dev proxy is configured in `src/setupProxy.js` (only `/api` routes proxied to `localhost:8000`; static assets served directly from `public/`)
- Backend reads `DATABASE_URL` from environment variables
- `DEV` environment variable controls whether scheduled tasks run
- Production deployment is on Heroku (radarvan-5e9c302c60e6.herokuapp.com)
- Static files served via explicit `serve_index()` route (returns `index.html` with `Cache-Control: no-cache`) followed by `StaticFiles` mount — ensures browser revalidates after deploys

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

## Key Technical Details

- **TypeScript**: Strict mode enabled, targeting ES6
- **Auto-generated code**: Files in `src/api/` are generated from OpenAPI spec - don't edit manually
- **Protobuf usage**: Match data structures are defined in proto files and compiled to TypeScript
- **Database migrations**: Managed with Alembic (config in `alembic.ini`)
- **Cloud integration**: Replay files and parsed JSON are stored in S3 (`s3://generals-stats/radarvan/dev/`) via `fsspec`; local filesystem is not used for replays
- **Player name resolution**: `resolve_player_name(name, color)` handles name aliases/overrides; used in player stats and superlatives
- **Frontend format toggles**: `FORMAT_OPTIONS` arrays drive ToggleButtonGroup; selected format is passed as `gameFormat` query param; state is reset on format change
