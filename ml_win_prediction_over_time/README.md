# Win-probability-over-time model

Predict **P(team A wins) at every point in a match** from the in-game event
stream — an esports-style win-probability curve. This is distinct from the
pre-game outcome model in [`../ml`](../ml): that one predicts the winner from the
match's *inputs* (players, generals, map); this one *watches the game unfold*
(builds, kills, captures, money) and updates its prediction over time.

ML deps live in the non-default `ml` dependency-group (they never ship to the
production app):

```bash
uv sync --group ml
```

## How it works

- **Source data**: the parsed replay JSON in S3 (`EnhancedReplayV2.stats`), which
  carries frame-stamped `buildEvents` / `killEvents` / `captureEvents` and a
  per-player money `timeSeries`. Only `player_rating.is_ratable_team_game`
  matches with exactly two human sides are used (label = did team A win).
- **Features** (`features.py`): the match is bucketed into 30-second windows.
  Each window holds, per side, cumulative *money, units built, structures built,
  build value, kills, value destroyed, captures* (log1p), plus the side-vs-side
  differences and elapsed fraction → `N_FEATURES` per timestep.
- **Model** (`model.py`): a **causal GRU** (only sees the past, like a live bar)
  emitting a win logit per timestep, trained with a time-weighted masked BCE —
  every timestep is supervised against the final outcome, later windows weighted
  more since the game is more decided.

## Pipeline

```bash
# 1. Snapshot competitive matches' event streams from the DB + S3 (frozen file).
DATABASE_URL=... uv run --group ml python -m ml_win_prediction_over_time.snapshot
#   -> data/snapshot-<date>.jsonl.gz (+ .manifest.json)

# 2. Temporal train/dev split; freezes feature-standardization stats from train.
uv run --group ml python -m ml_win_prediction_over_time.split \
    data/snapshot-<date>.jsonl.gz
#   -> data/split-<date>-temporal/{train,dev}.jsonl.gz, feature_stats.json, split.json

# 3. Train (uses the GPU automatically; falls back to CPU if it can't launch a kernel).
uv run --group ml python -m ml_win_prediction_over_time.train \
    data/split-<date>-temporal/
#   -> .../runs/<ts>/{best.ckpt,feature_stats.json,config.json}

# 4a. Win-probability curve for one match (fetches the replay; needs DATABASE_URL).
DATABASE_URL=... uv run --group ml python -m ml_win_prediction_over_time.predict \
    data/split-<date>-temporal/runs/<ts>/ --match-id 12345

# 4b. Evaluate on dev vs the 0.5 coin-flip baseline.
uv run --group ml python -m ml_win_prediction_over_time.predict \
    data/split-<date>-temporal/runs/<ts>/ --eval
```

**Early stopping does not watch dev.** `TrainConfig.val_frac` (default 0.15)
holds back the most recent slice of *train* for the best-checkpoint pick, so
`--eval` scores a set that had no hand in choosing the weights. This trainer
used to validate on `dev.jsonl.gz` itself — the same bug as in `../ml`, where
removing it cost the headline AUC ~0.06 of inflation. Any number produced before
this fix is optimistic.


## Layout

| file | role |
|---|---|
| `config.py` | bucketing constants + hyperparameters (torch-free dataclasses) |
| `snapshot.py` | DB + S3 → frozen per-match event records (`record_from_replay` is pure) |
| `features.py` | record → `[T, N_FEATURES]` sequence; `FeatureStats` standardization (torch-free) |
| `dataset.py` | torch `Dataset` / ragged-pad collate / `DataModule` |
| `model.py` | causal GRU + Lightning module (time-weighted masked BCE) |
| `split.py` | snapshot → temporal train/dev + frozen feature stats |
| `train.py` | training CLI (GPU) |
| `predict.py` | CPU inference (win-prob curve) + dev evaluation |

## Notes / next steps

- First cut handles **two-sided** games only (most ratable team games). FFA and
  >2 teams are skipped in `record_from_replay`.
- Not yet re-measured after the validation fix: the shipped
  `ml_winprob_over_time.onnx` predates it, so its quoted quality is the inflated
  kind. Retrain and re-score before quoting a number from it.
- Natural extensions: temperature-calibrate like `ml/train.py`, add categorical
  general/faction embeddings, ONNX-export for torch-free serving, and surface the
  curve in the match-detail UI alongside the replay playback.
