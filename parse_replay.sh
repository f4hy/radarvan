#!/usr/bin/env bash
# Parse a .rep file through cncstats and save the JSON it returns.
#
#   ./parse_replay.sh <replay.rep> [output.json]
#
# Output defaults to the replay's basename with a .json extension.
# Requires CNCSTATS_APIKEY - the Bearer token for POST /replay. (Not
# CNCSTATS_API_KEY, which is the X-API-Key for the map registry.)
set -euo pipefail

BASE_URL=${CNCSTATS_URL:-https://cncstats.computersrfun.org}

die() {
    echo "$*" >&2
    exit 1
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
    die "usage: $0 <replay.rep> [output.json]"
fi

replay=$1
[[ -f $replay ]] || die "no such replay file: $replay"
[[ -n ${CNCSTATS_APIKEY:-} ]] || die "CNCSTATS_APIKEY is not set"

if [[ $# -eq 2 ]]; then
    out=$2
else
    base=${replay##*/}
    out="${base%.rep}.json"
fi

body=$(mktemp)
trap 'rm -f "$body"' EXIT

code=$(curl -sS -o "$body" -w '%{http_code}' \
    -H "Authorization: Bearer ${CNCSTATS_APIKEY}" \
    -F "file=@${replay}" \
    "${BASE_URL}/replay")

if [[ $code != 2* ]]; then
    echo "cncstats returned HTTP $code:" >&2
    head -c 2000 "$body" >&2
    echo >&2
    exit 1
fi

if command -v jq >/dev/null; then
    # Pretty-print into a temp first so a bad response can't clobber $out.
    pretty=$(mktemp)
    trap 'rm -f "$body" "$pretty"' EXIT
    if ! jq . "$body" >"$pretty"; then
        echo "cncstats returned non-JSON:" >&2
        head -c 2000 "$body" >&2
        echo >&2
        exit 1
    fi
    mv "$pretty" "$out"
else
    cp "$body" "$out"
fi

echo "wrote $out"
