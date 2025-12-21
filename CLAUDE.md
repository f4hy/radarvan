# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radarvan is a statistics tracking application for Command & Conquer: Generals Zero Hour. It consists of a React frontend and a FastAPI Python backend that scrapes game data, parses replay files, and provides various statistics endpoints.

## Common Commands

### Frontend (React)
- `npm start` - Start development server (proxies to localhost:5000)
- `npm run build` - Build production bundle
- `npm test` - Run tests
- `prettier --write .` - Format code (configured to omit semicolons)

### Backend (Python/FastAPI)
The backend lives in the `radarvan/` directory. Common tasks typically involve:
- Starting the FastAPI server (check for uvicorn or similar in deployment scripts)
- Running database migrations with alembic: `alembic upgrade head`
- Database connection string is read from `DATABASE_URL` environment variable

### Code Generation
- `npm run openapi-ts` - Generate TypeScript API client from OpenAPI spec
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
  - DebugData (debug view, only shown with `?debug=True` query param)
- **API Client**: `src/Client.ts` configures the auto-generated API client, switching between localhost:8000 (dev) and production Heroku endpoint based on NODE_ENV
- **Styling**: Uses Material-UI (@mui/material) with responsive theming
- **Charting**: Uses recharts library for data visualization

### Backend Structure
- **Main app**: `radarvan/main.py` - FastAPI application with CORS middleware and request timing
- **Database**: SQLAlchemy ORM with PostgreSQL, managed via `db_utils.py` and `db.py`
- **Key modules**:
  - `matches.py` - Match listing and retrieval endpoints
  - `match_details.py` - Detailed match statistics (costs, APM, upgrades, spending over time)
  - `player_stats.py` - Player-specific win/loss stats by general and faction
  - `general_stats.py` - General/faction-specific statistics
  - `replay_files.py` - Replay file management and storage (appears to use cloud storage)
  - `scrape_games.py` - Web scraping to gather new game data
  - `parse_replay.py` - Replay file parsing
  - `schedule.py` - Scheduled tasks (likely for scraping)
  - `db_utils.py` - Database session management and replay repository pattern
- **Data models**: Defined using Protocol Buffers in `proto/match.proto`, which defines:
  - Generals (USA, China, GLA factions and their variants)
  - Match information (players, teams, map, duration, winner)
  - Statistics (win/loss records, APM, costs, upgrades, spending over time)

### Data Flow
1. Game replays are collected (via scraping or manual upload)
2. Replays are parsed to extract match details (players, generals, teams, winner, costs, actions)
3. Data is stored in PostgreSQL database
4. FastAPI serves statistics via REST endpoints
5. React frontend fetches and displays data using auto-generated TypeScript client
6. Protocol buffers ensure type consistency between frontend and backend data structures

### Environment Configuration
- Frontend uses `package.json` proxy setting for local development (proxies to localhost:5000)
- Backend reads `DATABASE_URL` from environment variables
- `DEV` environment variable controls whether scheduled tasks run
- Production deployment is on Heroku (radarvan-5e9c302c60e6.herokuapp.com)

## Key Technical Details

- **TypeScript**: Strict mode enabled, targeting ES6
- **Auto-generated code**: Files in `src/api/` are generated from OpenAPI spec - don't edit manually
- **Protobuf usage**: Match data structures are defined in proto files and compiled to TypeScript
- **Database migrations**: Managed with Alembic (config in `alembic.ini`)
- **Cloud integration**: Replay files appear to be stored in cloud storage (not local filesystem)
