# Win-probability-over-time model

Predicts **P(team A wins) at every 30-second window of a match** from the
in-game event stream: an esports-style win-probability curve. It is separate
from the pre-game model in [`../ml`](../ml). That one predicts the winner from
the match's inputs (players, generals, map). This one watches the game unfold
and updates as it goes.

The curve is served on the match page's AI tab and in `MatchDetails`. It also
feeds the narrative, match-interest, game-night and superlatives code through
`radarvan/win_curve.py`.

## Setup

Training needs torch, which has no Python 3.14 wheel, so it runs in a separate
3.13 venv at `.venv-ml/`. The project's lockfile is resolved for 3.14 only and
doesn't contain torch, so name the torch packages explicitly:

```bash
uv venv --python 3.13 .venv-ml
uv export --group ml --no-hashes --no-emit-project > /tmp/ml-req.txt
uv pip install --python .venv-ml/bin/python \
  --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/cu124 \
  -r /tmp/ml-req.txt "torch==2.6.0" "lightning>=2.6.5" "torchmetrics>=1.9.0"
```

torch is pinned to the cu124 build because it still runs on Pascal GPUs (see
`pyproject.toml`). Every command below runs from the repo root with
`PYTHONPATH=.`. Only the snapshot step needs the database and S3.

## Pipeline

```bash
D=ml_win_prediction_over_time/data

# 1. Snapshot: DB + S3 -> $D/snapshot-<UTC date>.jsonl.gz (+ manifest with skip counts)
set -a; . ./.env; set +a
PYTHONPATH=. uv run python -m ml_win_prediction_over_time.snapshot

# 2. Split. --dev-frac 0 trains on everything (the rolling eval is the evaluation).
#    --drop kills alive is the shipped feature set.
PYTHONPATH=. .venv-ml/bin/python -m ml_win_prediction_over_time.split \
    $D/snapshot-<date>.jsonl.gz --dev-frac 0 --drop kills alive --out-dir $D/split-<name>

# 3. Train the GRU seed bag, then the GBDT.
for s in 11 22 33 44 55 66; do
  PYTHONPATH=. .venv-ml/bin/python -m ml_win_prediction_over_time.train $D/split-<name> --seed $s
done
PYTHONPATH=. .venv-ml/bin/python -m ml_win_prediction_over_time.gbdt $D/split-<name>

# 4. Export the bag into one ONNX graph and deploy the bundle to the repo root.
PYTHONPATH=. .venv-ml/bin/python -m ml_win_prediction_over_time.export $D/split-<name>/runs/*
```

Export deploys four files together: `ml_winprob_over_time.onnx` (the GRU bag),
`_stats.json`, `_prior.json` and `_gbdt.onnx`. Serving requires all four, and
export refuses a GBDT that was fit on different feature columns or delta lags
than the GRU. `winprob_inference.bundle_version()` hashes the bundle into
`match_details.DETAILS_VERSION`, so cached curves are recomputed after any
redeploy without a manual version bump.

## How it works

- **Data.** Parsed replay JSON (`EnhancedReplayV2.stats`): build, kill, capture
  and death events plus per-player money and income series. Only
  `player_rating.is_ratable_team_game` matches with **two equal-sized human
  teams** are used. Uneven games get no curve at serving either. That gate is
  in `snapshot.record_from_replay`, which training and serving share.
- **Labels are the winner the app shows** (`MatchInfo`, admin overrides
  included), applied in `snapshot.app_label`. A match is dropped if cncstats
  only estimated its winner (`estimatedWinner`) and no admin ruled on it, or if
  the replay's own win flags disagree with the app.
- **Kills** count only enemy units and structures with a build cost. That
  drops projectiles, debris, wrecks and mines: in one fixture a Tunnel
  Defender's missiles made up 90 of 571 "kills". Kills of structures are
  tagged so they get their own feature.
- **Features** (`features.py`). Per side, as running totals up to each window:
  money on hand, income, units built, structures built, build value, value
  destroyed, structure value destroyed and captures. All are log1p'd, and each
  comes as side A, side B and A minus B. On top of that: minutes elapsed (never
  the fraction of the match, which would leak the final length) and the
  pre-game prior. The feature groups are named, and `split --drop` and the
  rolling eval can drop any of them. `FeatureStats` stores the chosen columns,
  so training and serving always read the same ones.
- **No 40-minute cap.** Games run to their real end (the longest is about 66
  minutes). Events past the 2-hour safety cap are dropped, never folded into
  the last window.
- **The pre-game prior** (`pregame.py`) is a Bradley-Terry fit on the rosters,
  fed in as a constant column so the GRU learns how fast to discount it.
  Training games get **out-of-fold** logits: scored on its own training games
  the prior looks about 40% sharper than on unseen ones (logit spread 0.90 vs
  0.63), and the GRU would learn to over-trust it.
- **The model is the average of two halves.**
  - A causal GRU (`model.py`), bagged over 6 seeds. It's trained with a
    time-weighted masked BCE, and a held-out temperature is built into the
    ONNX graph.
  - A heavily regularised GBDT (`gbdt.py`) on the current window plus its
    change over the last 1 and 2 minutes.

  The GRU is better in the opening minutes, where it passes the prior through
  smoothly. The trees are better mid-game.

## Results

These come from a rolling-origin evaluation of `snapshot-20260928`: 5 cuts,
each scoring the block after it, giving 370 held-out matches. Log-loss is per
30-second window. Lower is better.

| | log-loss | AUC | 0-2m | 2-4m | 4-8m | 8-15m | 15-25m | 25m+ |
|---|---|---|---|---|---|---|---|---|
| coin flip | 0.693 | 0.500 | 0.693 | 0.693 | 0.693 | 0.693 | 0.693 | 0.693 |
| pre-game prior alone | 0.636 | 0.665 | 0.613 | 0.613 | 0.619 | 0.652 | 0.679 | 0.644 |
| static logistic (current window only) | 0.477 | 0.845 | 0.664 | 0.583 | 0.466 | 0.416 | 0.352 | 0.425 |
| GRU, 6 seeds | 0.389 | 0.901 | **0.598** | 0.521 | 0.378 | 0.315 | 0.246 | 0.331 |
| GBDT | 0.388 | 0.905 | 0.638 | 0.537 | 0.391 | 0.302 | 0.235 | **0.152** |
| **GRU + GBDT (served)** | **0.367** | **0.913** | 0.603 | **0.511** | **0.366** | **0.284** | **0.213** | 0.201 |

- **The GRU and GBDT tie on their own.** The GRU's memory of the whole game adds
  little over the current state plus its recent change.
- **Averaging them beats the GRU alone.** Paired bootstrap over matches:
  −0.022 [−0.044, −0.003]. Their errors differ, so averaging cancels some.

**Read these numbers with the noise floor in mind.** The same configuration
retrained with different seeds moves the whole-match log-loss by about 0.005,
and the 15-25m bin by about 0.024. The bootstrap intervals cover sampling
of matches only, not seed variance. Treat any difference under about 0.01, or
any difference after minute 15, as noise.

**Why the shipped feature set is what it is.** Each row is one change against
the full feature set, bagged over 3 seeds. A positive number means the change
made the model worse.

| change | whole-match log-loss vs full | verdict |
|---|---|---|
| in-sample prior instead of out-of-fold | +0.014 | out-of-fold kept |
| drop income | +0.011 | kept |
| drop structure value destroyed | +0.013 | kept |
| drop kill **count** | −0.005 | dropped: value destroyed already carries it |
| drop players alive | −0.001 | dropped: no measurable effect |
| flat time weights instead of late ×3 | +0.008 | within noise; late ×3 kept |

Final-window accuracy is not a useful metric here. By the last window the
loser usually has nothing left, so even the memoryless logistic scores 0.99.

### Tried and not shipped: an uncertainty band

Seed-to-seed disagreement didn't flag worse predictions at all. Disagreement
between **bootstrap**-trained members did, from minute 4 on: at the same stated
confidence, log-loss was +0.074 higher where the band was wide, CI [+0.027,
+0.122]. Before minute 4 it predicted nothing. The band worked, but we chose
the cleaner chart without it. Bringing it back would mean bootstrap members in
training, per-member ONNX outputs and a range area on the chart.

## Evaluating a change

```bash
D=ml_win_prediction_over_time/data
PYTHONPATH=. .venv-ml/bin/python -m ml_win_prediction_over_time.rolling_eval run \
    $D/snapshot-<date>.jsonl.gz --name <name> [--drop <groups>] [--seeds 11 22 33] \
    [--late-weight 3] [--in-sample-prior]
PYTHONPATH=. .venv-ml/bin/python -m ml_win_prediction_over_time.rolling_eval compare \
    $D/rolling-<a>:blend $D/rolling-<b>:blend
```

`run` trains the served model at every cut and scores it next to the baselines,
saving every window's prediction. `compare` runs a paired bootstrap over
matches, by minute bin. Compare against a reseeded run of the same
configuration before believing a small difference.

## Layout

| file | role |
|---|---|
| `config.py` | bucketing constants and hyperparameters (torch-free) |
| `snapshot.py` | DB + S3 → per-match event records; `record_from_replay` (shared with serving), `app_label` |
| `features.py` | record → feature sequence; named feature groups; `FeatureStats`; `with_deltas` for the GBDT (torch-free) |
| `pregame.py` | the roster prior and its out-of-fold logits (torch-free) |
| `baselines.py` | coin flip, prior alone, static logistic, GBDT |
| `split.py` | snapshot → train/dev, freezing the prior and feature stats from train |
| `dataset.py`, `model.py`, `train.py` | the GRU: data module, model, training CLI |
| `gbdt.py` | the GBDT: fit and ONNX export |
| `predict.py` | `load_run`, CPU curves, a single-split `--eval`, a curve for one `--match-id` |
| `rolling_eval.py` | rolling-origin evaluation and paired comparison |
| `export.py` | GRU bag → ONNX, plus deploying the serving bundle |

Serving lives in `radarvan/winprob_inference.py`. It is torch-free and
sklearn-free: onnxruntime plus this package's torch-free modules.

## Known gaps

- **Serving's winner comes from the replay, not the app.** The curve's
  `actual_winner`, and serving's requirement that a winner exists, come from
  the replay's win flags, while training uses the app's result. For a match an
  admin overrode after it was parsed, the chart can name a different winner
  than the match header, or show no curve at all.
- **The blend rule is written twice.** The GRU+GBDT average appears by hand in
  `winprob_inference` and in `rolling_eval`. Building the GBDT into the single
  ONNX graph would leave one definition.
- **The skl2onnx export carries a workaround.** `gbdt.export_gbdt` patches a
  skl2onnx 1.20 bug (it passes a Python bool where onnx ≥ 1.20 requires an
  int), and `pyproject.toml` caps skl2onnx below 1.21 so that an upgrade forces
  someone to check whether the patch is still needed.
- **Only even two-sided team games are covered.** FFA, more than two teams, and
  uneven teams get no curve.
