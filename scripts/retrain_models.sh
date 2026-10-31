#!/usr/bin/env bash
#
# Retrain and deploy every served model from the DB in .env, then write an
# old-vs-new report (ml/retrain_report.py):
#   pre-game ensemble -> ml_ensemble/, composition model -> ml_scenario/,
#   win-prob bundle   -> ml_winprob_bundle/
# The previous artifacts are copied to ml/data/retrain-<date>/old/ first.
#
# Usage: scripts/retrain_models.sh          (K=50 for more ensemble replicates)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
: "${DATABASE_URL:?DATABASE_URL must be set (in .env or the environment)}"

K="${K:-30}"
PY_ML="${VENV_ML:-.venv-ml}/bin/python"
WP_SEEDS=(11 22 33 44 55 66)
export PYTHONPATH="$PWD"

[[ -x "$PY_ML" ]] || { echo "no ML venv at $PY_ML - run ./run_ml.sh once to create it" >&2; exit 1; }

STAMP=$(date -u +%Y%m%d)
OUT="ml/data/retrain-$STAMP"
PG_SNAP="ml/data/snapshot-$STAMP.jsonl.gz"
PG_SPLIT="ml/data/split-$STAMP-temporal"
WP_DIR="ml_win_prediction_over_time/data"
WP_SNAP="$WP_DIR/snapshot-$STAMP.jsonl.gz"
WP_SPLIT="$WP_DIR/split-$STAMP-full"

for d in "$OUT" "$PG_SPLIT" "$WP_SPLIT"; do
  if [[ -e "$d" ]]; then
    echo "$d already exists (retrained today already?) - remove it to rerun" >&2
    exit 1
  fi
done

latest_before_today() { ls -d "$@" 2>/dev/null | grep -v "$STAMP" | sort | tail -1 || true; }
PREV_PG_SPLIT=$(latest_before_today ml/data/split-[0-9]*-temporal)
PREV_WP_SNAP=$(latest_before_today "$WP_DIR"/snapshot-*.jsonl.gz)

LOGS="$OUT/logs"
mkdir -p "$OUT/old" "$LOGS"
cp -r ml_ensemble ml_scenario ml_winprob_bundle "$OUT/old/"
echo "==> backed up current artifacts to $OUT/old (logs in $LOGS)"
ROLLBACK="rm -rf ml_ensemble ml_scenario ml_winprob_bundle && cp -r $OUT/old/* ."
trap 'echo "FAILED - some models may already be deployed; roll back with: $ROLLBACK" >&2' ERR

echo "==> [1/5] snapshots (pre-game from DB, win-prob from DB + S3, in parallel)"
uv run python -m ml.snapshot >"$LOGS/pregame_snapshot.log" 2>&1 &
pg_pid=$!
uv run python -m ml_win_prediction_over_time.snapshot >"$LOGS/winprob_snapshot.log" 2>&1 &
wp_pid=$!
wait "$pg_pid" || { echo "pre-game snapshot failed, see $LOGS/pregame_snapshot.log" >&2; exit 1; }
wait "$wp_pid" || { echo "win-prob snapshot failed, see $LOGS/winprob_snapshot.log" >&2; exit 1; }
[[ -f "$PG_SNAP" && -f "$WP_SNAP" ]] || { echo "expected $PG_SNAP and $WP_SNAP (UTC date rolled over?)" >&2; exit 1; }

echo "==> [2/5] composition model (CPU, in the background)"
uv run python -m ml.scenario_train "$PG_SNAP" >"$LOGS/scenario.log" 2>&1 &
sc_pid=$!

echo "==> [3/5] pre-game ensemble (K=$K)"
uv run python -m ml.split "$PG_SNAP" --mode temporal >"$LOGS/pregame_split.log" 2>&1
"$PY_ML" -m ml.bootstrap_matrix "$PG_SPLIT" --k "$K" >"$LOGS/bootstrap.log" 2>&1
"$PY_ML" -m ml.bootstrap_matrix "$PG_SPLIT" --k 0 --promote >>"$LOGS/bootstrap.log" 2>&1

echo "==> [4/5] win-prob bundle (${#WP_SEEDS[@]} GRU seeds + GBDT)"
"$PY_ML" -m ml_win_prediction_over_time.split "$WP_SNAP" --dev-frac 0 --drop kills alive \
  --out-dir "$WP_SPLIT" >"$LOGS/winprob_train.log" 2>&1
for s in "${WP_SEEDS[@]}"; do
  "$PY_ML" -m ml_win_prediction_over_time.train "$WP_SPLIT" --seed "$s" >>"$LOGS/winprob_train.log" 2>&1
done
"$PY_ML" -m ml_win_prediction_over_time.gbdt "$WP_SPLIT" >>"$LOGS/winprob_train.log" 2>&1
"$PY_ML" -m ml_win_prediction_over_time.export "$WP_SPLIT"/runs/* >>"$LOGS/winprob_train.log" 2>&1

wait "$sc_pid" || { echo "composition model failed, see $LOGS/scenario.log" >&2; exit 1; }

echo "==> [5/5] report"
uv run python -m ml.retrain_report --old "$OUT/old" --out "$OUT" \
  --pregame-split "$PG_SPLIT" ${PREV_PG_SPLIT:+--prev-pregame-split "$PREV_PG_SPLIT"} \
  --winprob-snapshot "$WP_SNAP" ${PREV_WP_SNAP:+--prev-winprob-snapshot "$PREV_WP_SNAP"} \
  2>"$LOGS/report.log"

echo "==> deployed. Report: $OUT/report.md. Restart the API to load the new models;"
echo "    to roll back: $ROLLBACK"
