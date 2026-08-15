# Environment variables

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
