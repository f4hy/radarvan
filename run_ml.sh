#!/usr/bin/env bash
#
# Build the production win-prediction ensemble: snapshot -> split -> bootstrap
# ensemble (K resampled + reseeded replicates) -> promote to ml_ensemble/ (see
# ml/bootstrap_matrix.py). Auto-discovers each step's dated output to feed the
# next, same as before - just ending in an ensemble instead of one model.
#
# torch/lightning have no Python 3.14 wheel yet (see pyproject.toml's `ml`
# dependency-group comment), so training runs in a separate 3.13 venv this
# script creates on first use (VENV_ML, default .venv-ml/ - git-ignored,
# ~2-3GB with CUDA torch, one-time cost). Its non-torch deps are `uv export`'d
# from the current lockfile so they can't silently drift from pyproject.toml;
# torch/lightning/torchmetrics are pinned separately (same versions as
# pyproject.toml's `ml` group) since the lockfile excludes them under 3.14.
#
# Usage:
#   ./run_ml.sh                  # full pipeline: snapshot -> split -> ensemble -> promote
#   ./run_ml.sh --no-promote     # build the ensemble, review results.json before promoting
#   K=50 ./run_ml.sh             # more replicates (default 30)
#   MODE=random ./run_ml.sh      # random split instead of temporal
#
# Per-replicate training progress (val_loss etc.) prints as it goes; there's
# no separate "eval" step here since a single replicate's accuracy isn't the
# point - see ml/bootstrap_matrix.py's significant-cell summary at the end,
# or run `ml.predict <a replicate's run_dir> --eval` manually for a normal
# accuracy-vs-baselines read on one of them.
#
# Extra args (besides --no-promote) pass through to ml.bootstrap_matrix, e.g.
# `./run_ml.sh --base-seed 99` for a different bootstrap seed.
set -euo pipefail
cd "$(dirname "$0")"

# --- load env ----------------------------------------------------------
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
K="${K:-30}"
VENV_ML="${VENV_ML:-.venv-ml}"
RUN="uv run python -m"   # snapshot/split are torch-free; normal project env

PROMOTE=1
BOOTSTRAP_ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--no-promote" ]]; then
    PROMOTE=0
  else
    BOOTSTRAP_ARGS+=("$arg")
  fi
done

export PYTHONPATH="$(pwd)"
PY_ML="$VENV_ML/bin/python"

# --- 0. training venv (3.13; torch has no cp314 wheel yet) -----------------
if [[ ! -x "$PY_ML" ]]; then
  echo "==> [0/4] creating $VENV_ML (Python 3.13 + torch, one-time)"
  uv venv --python 3.13 "$VENV_ML"
  uv export --no-dev --group ml --no-header --no-annotate --no-editable --no-hashes \
    | uv pip install --python "$PY_ML" \
        --index-strategy unsafe-best-match \
        --extra-index-url https://download.pytorch.org/whl/cu124 \
        -r - "torch==2.6.0" "lightning>=2.4.0" "torchmetrics>=1.5.0"
fi

# --- 1. snapshot -------------------------------------------------------
echo "==> [1/4] snapshot (competitive matches from DB)"
$RUN ml.snapshot
SNAPSHOT=$(ls -t ml/data/snapshot-*.jsonl.gz | head -1)
echo "    snapshot: $SNAPSHOT"

# --- 2. split ------------------------------------------------------------
echo "==> [2/4] split ($MODE)"
$RUN ml.split "$SNAPSHOT" --mode "$MODE"
SPLIT=$(ls -dt ml/data/split-*-"$MODE"/ | head -1)
echo "    split: $SPLIT"

# --- 3. bootstrap ensemble -----------------------------------------------
echo "==> [3/4] bootstrap ensemble (K=$K, ~10-20s/replicate on GPU)"
"$PY_ML" -m ml.bootstrap_matrix "$SPLIT" --k "$K" "${BOOTSTRAP_ARGS[@]}"

# --- 4. promote ------------------------------------------------------------
if [[ "$PROMOTE" == 1 ]]; then
  echo "==> [4/4] promoting to ml_ensemble/ (what the app actually serves)"
  "$PY_ML" -m ml.bootstrap_matrix "$SPLIT" --k 0 --promote
  echo "==> done. Restart/reload the app to pick up the new ml_ensemble/, then commit it."
else
  echo "==> [4/4] skipped (--no-promote) - review $SPLIT/bootstrap/results.json, then:"
  echo "    $PY_ML -m ml.bootstrap_matrix $SPLIT --k 0 --promote"
fi
