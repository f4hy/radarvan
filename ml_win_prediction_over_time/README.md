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
  differences, **minutes elapsed**, and the **frozen pre-game prior** →
  `N_FEATURES` = 23 per timestep.
- **The pre-game prior** (`pregame.py`): a 17-parameter Bradley-Terry fit on the
  rosters, frozen from the train split like `FeatureStats`, fed in as a constant
  column. Measured: for the first ~4 minutes the sequence model was *worse* than
  simply knowing who was playing (log-loss 0.698 vs 0.644 over minutes 0-2),
  because almost nothing has happened yet. With the prior as an input the GRU
  learns how fast to discount it instead of spending four minutes catching up.
- **Elapsed time is minutes, not fraction-of-match.** The old feature was
  `bucket / n_buckets`, and `n_buckets` came from the match's *total* duration -
  so the model was told how long the game would last, which no live bar can
  know. Swapping it is a dead heat on log-loss (+0.0006, 95% CI [-0.0082,
  +0.0094]), so it costs nothing and makes the "same information a live bar
  would have" claim true.
- **Model** (`model.py`): a **causal GRU** (only sees the past, like a live bar)
  emitting a win logit per timestep, trained with a time-weighted masked BCE —
  every timestep is supervised against the final outcome, later windows weighted
  more since the game is more decided. A post-hoc temperature is fitted on the
  held-out validation tail and **baked into the ONNX graph**, so the served curve
  is calibrated rather than merely claiming to be.

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
holds back the most recent slice of *train* for the best-checkpoint pick and the
temperature fit, so `--eval` scores a set that had no hand in choosing the
weights. This trainer used to validate on `dev.jsonl.gz` itself — the same bug as
in `../ml`, where removing it cost the headline AUC ~0.06 of inflation. Any
number produced before this fix is optimistic.
`TrainConfig.refit_on_full` (default on) then refits on the whole train split for
the chosen number of epochs, so holding the tail back costs no training data.

## Results (rolling origin, snapshot-20260828)

Five cuts across the corpus, three seeds bagged at each, scoring the block after
each cut: **435 held-out matches, 12,776 timesteps.** Reported by game phase,
because a single pooled number hides everything interesting — late in a decided
game every predictor looks brilliant.

| | log-loss | acc | AUC | first 20% | 20-40% | 40-60% | 60-80% | last 20% |
|---|---|---|---|---|---|---|---|---|
| coin flip | 0.6931 | 0.501 | 0.500 | 0.693 | 0.693 | 0.693 | 0.693 | 0.693 |
| pre-game prior alone | 0.6636 | 0.599 | 0.639 | 0.667 | 0.663 | 0.662 | 0.663 | 0.662 |
| `static_logistic` | 0.5563 | 0.681 | 0.769 | 0.718 | 0.673 | 0.626 | 0.546 | 0.265 |
| GRU, previous design | 0.4843 | 0.752 | 0.850 | 0.702 | 0.640 | 0.534 | 0.398 | 0.199 |
| **GRU, shipped** | **0.4568** | **0.763** | **0.861** | **0.678** | **0.615** | **0.496** | 0.373 | 0.174 |

Paired bootstrap over matches, shipped minus previous design:

| window | difference | 95% CI | P(better) |
|---|---|---|---|
| whole match | −0.0314 | [−0.0624, +0.0006] | 0.97 |
| first 4 minutes | **−0.0499** | [−0.0785, −0.0194] | **1.00** |
| first 2 minutes | **−0.0626** | [−0.0883, −0.0361] | **1.00** |

The gain is exactly where it was designed to be — the opening minutes — and the
whole-match figure straddles zero, so quote the early-game numbers, not the
pooled one. Against the bars it must clear the model is unambiguous: −0.118
against `static_logistic` and −0.215 against the pre-game prior, both P = 1.00.

Two things that are *not* wins and should not be reported as such: the
temperature is worth 0.025 log-loss on a single dev slice but ±0.000 under the
rolling protocol (`refit_on_full` already absorbs most of the overconfidence), and
the elapsed-time swap is a dead heat. Both were kept for correctness, not score.

**Final-timestep accuracy is not a metric here.** It is 0.98 for the GRU *and*
0.99 for the memoryless logistic: by the last window the loser has no buildings
left. The old `--eval` reported it as a headline.


## Layout

| file | role |
|---|---|
| `config.py` | bucketing constants + hyperparameters (torch-free dataclasses) |
| `snapshot.py` | DB + S3 → frozen per-match event records (`record_from_replay` is pure) |
| `features.py` | record → `[T, N_FEATURES]` sequence; `FeatureStats` standardization (torch-free) |
| `pregame.py` | the frozen roster prior fed in as a feature (torch-free) |
| `baselines.py` | coin flip + the memoryless "read the scoreboard" logistic (torch-free) |
| `dataset.py` | torch `Dataset` / ragged-pad collate / `DataModule` |
| `model.py` | causal GRU + Lightning module (time-weighted masked BCE) |
| `split.py` | snapshot → temporal train/dev + frozen feature stats |
| `train.py` | training CLI (GPU) |
| `predict.py` | CPU inference (win-prob curve) + dev evaluation |

## Notes / next steps

- First cut handles **two-sided** games only (most ratable team games). FFA and
  >2 teams are skipped in `record_from_replay`.
- Natural extensions: add categorical general/faction embeddings, and surface the
  curve in the match-detail UI alongside the replay playback.
- The serving bundle is three files, all deployed together by
  `export.py`: `ml_winprob_over_time.onnx`, `..._stats.json`, and
  `..._prior.json`. A model exported before the prior existed still loads —
  `PregamePrior.neutral()` reproduces the all-zero column it was trained on —
  but the shapes differ (22 vs 23 features), so old and new artifacts cannot be
  mixed.
