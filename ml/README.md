# Radarvan match-outcome ML

Predict the winner of a Zero Hour match from its pre-game inputs (players, teams,
generals, map). Design and rationale: **[model_design.md](model_design.md)**.

ML deps live in the non-default `ml` dependency-group, so they never ship to the
production app. `torch`/`lightning`/`torchmetrics` have no Python 3.14 wheel yet
(the main app targets 3.14), so **training needs a separate 3.13 venv** —
`uv sync` in the project's own 3.14 env refuses a 3.13 interpreter
(`requires-python = ">=3.14"`), so build it outside the project instead:

```bash
uv venv --python 3.13 /path/to/some/venv-ml
uv pip install --python /path/to/some/venv-ml/bin/python \
  --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/cu124 \
  --group ml -e .   # torch==2.6.0+cu124 pinned for Pascal (sm_50/sm_60) GPUs; see pyproject.toml
```

Everything below assumes that venv's `python` (with `PYTHONPATH` at the repo
root) for the training/export/ensemble steps; the snapshot/split steps don't
need torch and can run in the normal project env (`uv run python -m ...`).

On this machine that venv is `.venv-ml/` at the repo root, so the training
steps read:

```bash
PYTHONPATH=$PWD .venv-ml/bin/python -m ml.train ...
```

Because it runs 3.13, every `radarvan/` module `ml/` imports has to stay
3.13-parseable — notably no unparenthesized `except A, B:` (PEP 758 makes that
valid on the app's 3.14, and it is a SyntaxError here; it broke `ml.train` at
`player_role.py` once). `tests/test_ml_venv_imports.py` guards it.

## Pipeline

Steps 1-2 (snapshot, split) and 5 (export) are torch-free; 3/4/6/7 need the
3.13 ml venv above.

```bash
# 1. Snapshot the trainable matches from the DB into a frozen file: the games
#    that move ratings, i.e. team games + tournament 1v1s. Casual 1v1s are out
#    (measured - see model_design.md). ml.snapshot.is_training_match.
DATABASE_URL=... uv run python -m ml.snapshot
#   -> ml/data/snapshot-<date>.jsonl.gz (+ .manifest.json)

# 2. Split into train/dev and freeze the vocab from train only. 1v1s always go
#    to train (they're recent, so a plain temporal cut puts them all in dev and
#    "1v1" never reaches the vocab); --holdout-1v1 opts out. split.json records
#    n_train_1v1/n_dev_1v1.
uv run python -m ml.split ml/data/snapshot-<date>.jsonl.gz --mode temporal
#   -> ml/data/split-<date>-temporal/{train,dev}.jsonl.gz, vocab.json, split.json

# 3. Train a single model (uses the GPU automatically; checkpoint is
#    device-agnostic) - for quick iteration/ablations, not what gets served.
uv run python -m ml.train ml/data/split-<date>-temporal/
#   -> .../runs/<ts>/{best.ckpt,vocab.json,config.json}

# 4. Evaluate on CPU vs baselines (coin flip, openskill predict_win).
uv run python -m ml.predict ml/data/split-<date>-temporal/runs/<ts>/ --eval

# 4b. Predict a single match by id (fetches from the DB; needs DATABASE_URL).
uv run python -m ml.predict <run_dir> --match-id 12345

# 5. Export a single model to ONNX (calibration baked in) - useful to sanity
#    check one run; production serves the ensemble from step 6, not this.
uv run python -m ml.export            # most recently trained run
uv run python -m ml.export <run_dir>  # a specific run
#   -> <run_dir>/model.onnx (+ onnx_meta.json with the input spec)

# 6. Build the production ensemble: K bootstrap-resampled, reseeded replicates
#    (~1000 train matches is too little to trust any single model's point
#    estimate - see ml/bootstrap_matrix.py's docstring and the faction-matrix
#    write-up it grew out of). Prints which effects survive vs. look like noise.
uv run python -m ml.bootstrap_matrix ml/data/split-<date>-temporal/ --k 30
#   -> ml/data/split-<date>-temporal/bootstrap/{boot-NNN/, results.json}

# 7. Once you're happy with results.json, promote it to what the app serves
#    (radarvan/ml_inference.py reads ML_ENSEMBLE_DIR, default ml_ensemble/ at
#    the repo root) - re-run with --k 0 to promote without retraining.
uv run python -m ml.bootstrap_matrix ml/data/split-<date>-temporal/ --k 0 --promote
#   -> ml_ensemble/{model-000.onnx..model-NNN.onnx, vocab.json}
# Commit ml_ensemble/ like any other deployed artifact (see repo root README.md).
```

`model.onnx` takes the 12 tensors `ml.dataset.collate` produces (encode with the
run's `vocab.json`) and outputs the calibrated `prob_team_a`. Serve it with
`onnxruntime` alone — no torch needed. Export verifies torch/ONNX parity
(~1e-7) before writing. Every replicate in the ensemble shares one vocab (frozen
once, from the same split each was resampled from), so they're interchangeable
at inference time — see `radarvan/ml_inference.py`.

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
| `bootstrap_matrix.py` | builds the production N-model ensemble (bootstrap resample + reseed, retrain, `--promote`) |
| `dump_matrix_worker.py` | standalone single-model UNK/UNK matrix dump; the per-replicate worker `bootstrap_matrix.py` shells out to |
| `matchup_support.py` | how many real games back each general-vs-general cell (diagnostic, not wired into serving) |
