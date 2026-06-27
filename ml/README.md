# Radarvan match-outcome ML

Predict the winner of a Zero Hour match from its pre-game inputs (players, teams,
generals, map). Design and rationale: **[model_design.md](model_design.md)**.

ML deps live in the non-default `ml` dependency-group, so they never ship to the
production app. Install them locally:

```bash
uv sync --group ml
```

## Pipeline

```bash
# 1. Snapshot competitive matches from the DB into a frozen, versioned file.
DATABASE_URL=... uv run python -m ml.snapshot
#   -> ml/data/snapshot-<date>.jsonl.gz (+ .manifest.json)

# 2. Split into train/dev and freeze the vocab from train only.
uv run python -m ml.split ml/data/snapshot-<date>.jsonl.gz --mode temporal
#   -> ml/data/split-<date>-temporal/{train,dev}.jsonl.gz, vocab.json, split.json

# 3. Train (uses the GPU automatically; checkpoint is device-agnostic).
uv run python -m ml.train ml/data/split-<date>-temporal/
#   -> .../runs/<ts>/{best.ckpt,vocab.json,config.json}

# 4. Evaluate on CPU vs baselines (coin flip, openskill predict_win).
uv run python -m ml.predict ml/data/split-<date>-temporal/runs/<ts>/ --eval

# 4b. Predict a single match by id (fetches from the DB; needs DATABASE_URL).
uv run python -m ml.predict <run_dir> --match-id 12345

# 5. Export to ONNX for portable, torch-free CPU serving (calibration baked in).
uv run python -m ml.export            # most recently trained run
uv run python -m ml.export <run_dir>  # a specific run
#   -> <run_dir>/model.onnx (+ onnx_meta.json with the input spec)
```

`model.onnx` takes the 12 tensors `ml.dataset.collate` produces (encode with the
run's `vocab.json`) and outputs the calibrated `prob_team_a`. Serve it with
`onnxruntime` alone — no torch needed. Export verifies torch/ONNX parity
(~1e-7) before writing.

## Ablations

The model is three additive, individually-toggleable terms (individual strength,
teammate synergy, general matchup). Train the linear floor / drop terms to measure
each contribution:

```bash
uv run python -m ml.train <split>/ --no-mlp        # Bradley-Terry / openskill-like floor
uv run python -m ml.train <split>/ --no-synergy
uv run python -m ml.train <split>/ --no-matchup
```

## Layout

| file | role |
|---|---|
| `config.py` | hyperparameters / paths (dataclasses, torch-free) |
| `snapshot.py` | DB → frozen snapshot + manifest |
| `split.py` | snapshot → train/dev + frozen vocab |
| `features.py` | `MatchInfo` → encoded ints; `Vocab` (torch-free) |
| `dataset.py` | torch `Dataset` / collate / `DataModule` |
| `model.py` | DeepSet + synergy + matchup model + Lightning module |
| `train.py` | training CLI (GPU) |
| `predict.py` | CPU inference + baseline/metric harness |
