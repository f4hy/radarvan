#!/usr/bin/env bash
#
# Snapshot the production database to db_snapshots/ for local use.
#
#   ./scripts/db_snapshot.sh              # skip match_details_cache rows (~45MB)
#   ./scripts/db_snapshot.sh --full       # everything, cache included (~220MB)
#   ./scripts/db_snapshot.sh -o my.dump   # explicit output path
#
# READ-ONLY against production: pg_dump only takes ACCESS SHARE locks.
#
# pg_dump runs inside a postgres:17 container, so no local Postgres client is
# needed and the client major version always matches the server (17.x).
#
# Source URL resolution, in order:
#   1. --source <url>
#   2. $PROD_DATABASE_URL
#   3. DATABASE_URL from ./.env
#   4. `heroku config:get DATABASE_URL -a $HEROKU_APP`
set -euo pipefail

cd "$(dirname "$0")/.."

PG_IMAGE="postgres:17-alpine"
OUT_DIR="db_snapshots"
FULL=0
OUT=""
SOURCE_URL="${PROD_DATABASE_URL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) FULL=1; shift ;;
    --source) SOURCE_URL="$2"; shift 2 ;;
    -o|--output) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$SOURCE_URL" && -f .env ]]; then
  raw="$(grep -E '^DATABASE_URL=' .env | tail -1 | cut -d= -f2- || true)"
  raw="${raw%\"}"; raw="${raw#\"}"; raw="${raw%\'}"; raw="${raw#\'}"
  SOURCE_URL="$raw"
fi

if [[ -z "$SOURCE_URL" ]] && command -v heroku >/dev/null 2>&1 && [[ -n "${HEROKU_APP:-}" ]]; then
  echo "==> reading DATABASE_URL from heroku app $HEROKU_APP"
  SOURCE_URL="$(heroku config:get DATABASE_URL -a "$HEROKU_APP")"
fi

if [[ -z "$SOURCE_URL" ]]; then
  echo "no source database URL found. Set PROD_DATABASE_URL, or DATABASE_URL in .env," >&2
  echo "or pass --source postgres://..." >&2
  exit 1
fi

SOURCE_URL="${SOURCE_URL/postgres:\/\//postgresql://}"

# Host, for the sanity check and the log line below -- never the credentials.
HOST="$(printf '%s' "$SOURCE_URL" | sed -E 's#^[^:]+://([^@]*@)?([^:/?]+).*#\2#')"
case "$HOST" in
  localhost|127.0.0.1|db|"")
    echo "refusing to snapshot '$HOST' -- this script is for snapshotting a" >&2
    echo "remote/production database, not the local compose one." >&2
    exit 1
    ;;
esac

mkdir -p "$OUT_DIR"
if [[ -z "$OUT" ]]; then
  suffix=$([[ $FULL -eq 1 ]] && echo "full" || echo "nocache")
  OUT="$OUT_DIR/radarvan-$(date -u +%Y%m%d-%H%M%S)-$suffix.dump"
fi

# match_details_cache is ~80% of the database and is pure derived data --
# radarvan rebuilds any row on demand (see match_details.DETAILS_VERSION), so
# excluding its rows keeps snapshots small. The table itself is still created.
EXCLUDE=()
if [[ $FULL -eq 0 ]]; then
  EXCLUDE=(--exclude-table-data=public.match_details_cache)
fi

echo "==> dumping $HOST -> $OUT"
[[ $FULL -eq 0 ]] && echo "    (match_details_cache rows excluded; pass --full to include them)"

# --no-owner/--no-privileges: prod roles (Heroku's generated user) don't exist
# locally; without these the restore emits an error for every OWNER TO / GRANT.
docker run --rm -i "$PG_IMAGE" \
  pg_dump --format=custom --compress=9 \
          --no-owner --no-privileges \
          "${EXCLUDE[@]}" \
          --dbname "$SOURCE_URL" \
  > "$OUT"

echo "==> wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo "    load it with: ./scripts/db_restore.sh"
