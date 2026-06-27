#!/usr/bin/env bash
#
# Run the full ML pipeline: snapshot -> split -> train -> eval.
#
# Loads env vars (DATABASE_URL, AWS creds, ...) from .env, then chains the four
# steps, auto-discovering each step's dated output to feed the next.
#
# Usage:
#   ./run_ml.sh                       # full pipeline, temporal split
#   MODE=random ./run_ml.sh           # random split instead
#   ./run_ml.sh --no-synergy          # extra args are passed through to train
#
set -euo pipefail
cd "$(dirname "$0")"

# --- load env --------------------------------------------------------------
if [[ -f .env ]]; then
  set -a            # export everything sourced
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "warning: no .env found; relying on existing environment" >&2
fi

: "${DATABASE_URL:?DATABASE_URL must be set (in .env or the environment)}"

MODE="${MODE:-temporal}"
RUN="uv run --group ml python -m"   # ensures the ml dependency-group is present

# --- 1. snapshot -----------------------------------------------------------
echo "==> [1/4] snapshot (competitive matches from DB)"
$RUN ml.snapshot
SNAPSHOT=$(ls -t ml/data/snapshot-*.jsonl.gz | head -1)
echo "    snapshot: $SNAPSHOT"

# --- 2. split --------------------------------------------------------------
echo "==> [2/4] split ($MODE)"
$RUN ml.split "$SNAPSHOT" --mode "$MODE"
SPLIT=$(ls -dt ml/data/split-*-"$MODE"/ | head -1)
echo "    split: $SPLIT"

# --- 3. train --------------------------------------------------------------
echo "==> [3/4] train (extra args: ${*:-none})"
$RUN ml.train "$SPLIT" "$@"
RUN_DIR=$(ls -dt "${SPLIT%/}"/runs/*/ | head -1)
echo "    run: $RUN_DIR"

# --- 4. eval ---------------------------------------------------------------
echo "==> [4/4] eval (model vs baselines on dev)"
$RUN ml.predict "$RUN_DIR" --eval

echo "==> done. run bundle: $RUN_DIR"
