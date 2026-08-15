#!/usr/bin/env bash
#
# Hydrate the LOCAL compose Postgres from a snapshot made by db_snapshot.sh.
#
#   ./scripts/db_restore.sh                    # newest file in db_snapshots/
#   ./scripts/db_restore.sh path/to/x.dump     # a specific snapshot
#
# This can only ever write to the compose `db` service: every statement goes
# through `docker compose exec db`, so there is no code path here that can
# reach production, whatever DATABASE_URL happens to say.
#
# The target database is dropped and recreated, then alembic is run so a
# snapshot older than your local migrations still ends up at head.
set -euo pipefail

cd "$(dirname "$0")/.."

DB_USER=radarvan
DB_NAME=radarvan

SNAPSHOT="${1:-}"
if [[ -z "$SNAPSHOT" ]]; then
  SNAPSHOT="$(ls -t db_snapshots/*.dump 2>/dev/null | head -1 || true)"
fi

if [[ -z "$SNAPSHOT" || ! -f "$SNAPSHOT" ]]; then
  echo "no snapshot found. Run ./scripts/db_snapshot.sh first." >&2
  exit 1
fi

echo "==> starting local db"
docker compose up -d --wait db

echo "==> dropping and recreating '$DB_NAME' (local container only)"
# WITH (FORCE) terminates the backend/migrate connections holding the database
# open; they reconnect through SQLAlchemy's pool afterwards.
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);" \
  -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "==> restoring $SNAPSHOT ($(du -h "$SNAPSHOT" | cut -f1))"
docker compose exec -T db pg_restore \
  --no-owner --no-privileges --dbname "$DB_NAME" --username "$DB_USER" \
  < "$SNAPSHOT"

echo "==> applying any migrations newer than the snapshot"
docker compose run --rm migrate

# The backend caches match data in-process at startup; restart it so it isn't
# serving results derived from whatever was in the database before.
if [[ -n "$(docker compose ps -q backend)" ]]; then
  echo "==> restarting backend"
  docker compose restart backend
fi

echo "==> done. Local database hydrated from $SNAPSHOT"
