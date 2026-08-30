# Local development

The whole stack — Postgres, the FastAPI backend, the Vite frontend — runs from
one command, against a **local** database you can freely break.

```bash
make up          # or: docker compose up
```

| | |
|---|---|
| Frontend | http://localhost:5173 |
| API + docs | http://localhost:8000 · http://localhost:8000/docs |
| Postgres | `localhost:5433`, user/password/db all `radarvan` |

Both sides hot-reload from the bind-mounted source: `fastapi dev` watches
`radarvan/`, Vite serves `src/` with HMR. Editing files on the host is all it
takes; no rebuild.

The dev servers are also perfectly runnable by hand (`fastapi dev
radarvan/main.py` + `npm start`) — that still works and still points at
whatever `DATABASE_URL` your shell has. The two ways compete for ports 8000 and
5173, so stop one before starting the other, or set `API_PORT` / `WEB_PORT` in
`.env` to move the compose stack out of the way.

## Prerequisites

- Docker with Compose v2
- A `.env` file (copy `.env.example`) with the AWS, cncstats, Discord and LLM
  keys you need. Compose reads it for secrets but **overrides `DATABASE_URL`**
  to point at the local container — nothing in the compose stack can reach
  production Postgres.

Replays and parsed JSON still come from the real S3 bucket, using your AWS
credentials. That's read-mostly; be aware that uploading a replay locally does
write to `s3://generals-stats/radarvan/dev/`.

`NOTIFY_WEB_HOOK` is blanked out for the compose backend so local runs can't
post to the team's Discord. Set `LOCAL_NOTIFY_WEB_HOOK` in `.env` if you're
specifically testing `notify()`.

## Everyday commands

```bash
make up            # start everything (detached)
make down          # stop, keeping the database
make logs          # tail all services
make ps            # what's running
make shell         # bash inside the backend container
make db-shell      # psql against the local database
make migrate       # alembic upgrade head against the local database
make up-build      # rebuild the images (after changing pyproject/package.json)
```

Dependency changes need an image rebuild: `uv.lock` and `package-lock.json` are
baked in at build time (`make up-build`).

**Use `make up-build`, not `make down && make up`, after adding a package.** The
frontend mounts a *named* volume (`radarvan_node_modules`) over
`/app/node_modules` so the container keeps the linux tree `npm ci` built in the
image rather than the host's. Named volumes survive `docker compose down`, so a
plain rebuild leaves the container running the **old** dependencies: the install
looks like it worked and Vite then fails at runtime with

```
Failed to resolve import "<the new package>" from "src/….tsx". Does the file exist?
```

`make up-build` drops that volume so it repopulates from the freshly built image.
`pgdata` is untouched — never reach for `docker compose down -v` to fix this, it
destroys your local database too (that's `make db-reset`'s job, deliberately).

## Hydrating from production

```bash
make db-snapshot   # dump prod -> db_snapshots/radarvan-<ts>-nocache.dump
make db-restore    # load the newest snapshot into the local database
```

`db-snapshot` is read-only against production (`pg_dump` takes only ACCESS
SHARE locks) and runs the dump inside a `postgres:17` container, so no local
Postgres client is required. It reads the source URL from `PROD_DATABASE_URL`,
else `DATABASE_URL` in `.env`, else `heroku config:get DATABASE_URL -a $HEROKU_APP`,
and refuses to run against localhost.

By default it **skips the rows of `match_details_cache`** — that one table is
80% of the database (175 MB of 222 MB) and is pure derived data that the app
rebuilds on demand from S3 in well under a second per match. A snapshot without
it is ~5 MB and takes ~6 seconds end to end. Use `make db-snapshot-full` if you
specifically need the cached rows.

`db-restore` drops and recreates the local database, restores the newest
snapshot (or a path you pass to `./scripts/db_restore.sh`), re-runs migrations
so a stale snapshot still lands at head, and restarts the backend to drop its
in-process caches. Every statement goes through `docker compose exec db`, so it
has no way to address anything but the local container.

Snapshots live in `db_snapshots/`, which is gitignored — they contain real user
data (Discord identities, uploads); don't pass them around.

## Testing a migration

This is the main reason the local database exists:

```bash
make db-snapshot && make db-restore     # real data, local
uv run alembic revision --autogenerate -m "..."
make migrate                            # apply it locally
make db-shell                           # inspect the result
```

If it goes wrong, `make db-restore` puts you back where you started, and
`make db-reset` wipes the volume entirely for an empty database at head.

### Why `scripts/bootstrap_db.py` exists

The compose `migrate` service runs `scripts/bootstrap_db.py`, not a bare
`alembic upgrade head`. The migration chain can't build the schema from
nothing: `4efb2f28e765_initial_migration` is an empty `pass` (alembic was
introduced against an already-populated production database and stamped onto
it), so later revisions ALTER tables no revision ever created — running the
chain against an empty database dies on `DROP TABLE generals`.

So the bootstrap branches: a database with an `alembic_version` table (a
restored snapshot) gets `alembic upgrade head` as normal, while an empty one
gets `Base.metadata.create_all()` plus `alembic stamp head`. Migrations you
write are still exercised properly — against restored production data, which is
the case that matters.

One consequence: an empty local database is built from the ORM models, so it
reflects `radarvan/db.py` rather than the sum of the migrations. If the two
have drifted, only the snapshot-restored database will show it.

## What isn't containerized

- **S3.** `replay_files` hardcodes the bucket and region, so pointing it at a
  MinIO container would take code changes. Local runs use the real bucket.
- **cncstats.** Replay parsing calls the live service with `CNCSTATS_APIKEY`.
- **Tests.** `make test` still runs on the host (`uv run pytest`); the suite
  never opens a real connection — see `tests/conftest.py`.
