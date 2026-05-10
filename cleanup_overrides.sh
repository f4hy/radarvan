#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"
START="2025-11-01"
END="2026-01-25"
LOG="cleanup_overrides.log"

: > "$LOG"

while read -r match_id; do
    info=$(curl -sf "$API/api/match/$match_id" || true)
    if [[ -z "$info" ]]; then
        continue
    fi
    match_date=$(printf '%s' "$info" | jq -r '.date // empty')
    if [[ -z "$match_date" ]]; then
        continue
    fi
    if [[ "$match_date" < "$START" ]] || [[ "$match_date" > "$END" ]]; then
        continue
    fi
    delete_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/api/override/$match_id")
    if [[ ! "$delete_code" =~ ^2 ]]; then
        printf 'FAILED delete %s http=%s\n' "$match_id" "$delete_code" >&2
        continue
    fi
    reparse_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/reparse/$match_id")
    if [[ ! "$reparse_code" =~ ^2 ]]; then
        printf 'FAILED reparse %s http=%s\n' "$match_id" "$reparse_code" >&2
        continue
    fi
    printf '%s %s\n' "$match_id" "$match_date" | tee -a "$LOG"
done < <(curl -sf "$API/api/overrides" | jq -r '.[].match_id')

printf 'Deleted overrides logged to %s\n' "$LOG"
