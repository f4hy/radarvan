# Radarvan match-outcome model — design

## Goal

Given the **pre-game** description of a match — the set of players, which team
each is on, the general (faction sub-type) each picked, and the map — predict
**which team wins**. Secondary (auxiliary) targets we may also predict: match
duration, per-player money earned, units/buildings built.

The headline metric is win prediction. Everything else is either a regulariser
(multi-task auxiliary loss) or a nice-to-have.

This is deliberately the *same prediction task the repo already solves* with the
openskill `PlackettLuce` model (`radarvan/player_rating.py:predict_win`) and
augments with the separate synergy (`player_synergy.py`) and general-matchup
(`team_stats.py` pair win/loss) analyses. The ML model's job is to **unify and
beat that ensemble** by learning those effects jointly and end-to-end. openskill
is therefore our primary baseline, not an afterthought.

## Why not just use openskill?

openskill gives each player one scalar (`mu`, `sigma`) and predicts a team as the
sum of player skills. It cannot represent:

- **player × general affinity** — some players are much stronger on specific
  generals;
- **player × map affinity** — map-specific strength;
- **teammate synergy** — pairs that over/under-perform their individual ratings
  (the repo models this *separately* in `player_synergy.py`);
- **general counter / matchup structure** — Toxin vs Infantry etc. (modelled
  separately as pair win/loss in `team_stats.py`);
- any **non-linear** interaction among the above.

A single jointly-trained model can capture all of these, and — importantly — can
*degrade gracefully* to the openskill solution when there isn't enough data
(that's what the linear ablation below is for).

## Hard constraints the architecture must satisfy

1. **Permutation invariance within a team.** The order players are listed on a
   team is arbitrary; the prediction must not depend on it.
2. **Antisymmetry across teams.** Swapping "team A" and "team B" must flip the
   predicted probability: `P(A) = 1 - P(B)`. We get this *structurally* (the head
   is a difference/softmax of per-team scores), so the model can never learn a
   "team 1 usually wins" slot bias and we don't need to randomise team order.
3. **Variable team size.** 1v1, 2v2, 3v3, and (rare) multi-team games must all
   flow through the same model. Set-pooling handles this.
4. **CPU inference.** Training uses the local NVIDIA GPU; inference must run on a
   (powerful) CPU. The model is tiny (embeddings + small MLP), so plain
   `torch` on CPU with `map_location="cpu"` is sufficient — no GPU-only ops, no
   custom kernels. Optional TorchScript/ONNX export is a later nicety.

## Feature engineering

Everything is derived from `api_types.MatchInfo` (see `radarvan/api_types.py`).
All player names are alias-resolved with `player_ids.resolve_player_name` *before*
vocab lookup — clients/replays use in-game aliases.

### Per-player categorical features (embedded)

| feature | cardinality | notes |
|---|---|---|
| `player_id` | ~ #known players + `UNK` | from `player_ids.PLAYER_NAMES`; anyone not in the training vocab → `UNK` |
| `general` | 12 + `UNK` | `api_types.General` (USA/AIR/LASER/SUPER, CHINA/NUKE/TANK/INFANTRY, GLA/TOXIN/STEALTH/DEMO) |
| `faction` | 3 + `UNK` | derived: `general // 4` → USA / China / GLA. Redundant with general but a useful coarse fallback for rare general×player combos |
| `starting_position` | small int + `UNK` | optional; map-relative spawn (0-based in replay). Many games randomise this, so it is **off by default** |

### Match-level categorical features (embedded, shared by both teams)

| feature | notes |
|---|---|
| `map_id` | canonicalised via `ReplayManager.resolve_map_name`; rare maps → `UNK` |
| `format` | composition category string ("1v1","2v2",...) — small embedding, mostly informs the size-normalisation |

Because the map is shared by both teams it has **no effect on the antisymmetric
output on its own** — only its *interactions* (player×map, general×map) move the
prediction. That is exactly what we want.

### Numeric features (optional, standardised)

- `openskill_mu`, `openskill_sigma` per player — a strong prior / warm start so
  the net only has to learn the *residual* structure on top of the existing
  rating. **Leakage caveat:** these must be computed from the **training games
  only** (or as-of the match date), never the full dataset, or dev metrics are
  optimistic. Off by default in v1; turn on once the leak-free as-of computation
  is wired in.

### Targets

- **Primary:** `winning_team` → for the canonical 2-team case, label `y = 1` if
  team-A won (team ordering is arbitrary but the head is antisymmetric, so the
  choice is irrelevant). Multi-team → categorical over teams.
- **Auxiliary (optional, multi-task):** `duration_minutes` (regression),
  per-team money/units (regression) — these need `MatchDetails`, pulled lazily
  and only used when present. Auxiliary losses are down-weighted and exist mainly
  to regularise the shared trunk.

### Data hygiene / filtering

Snapshot includes only games where `player_rating.is_ratable_team_game` is true:
competitive, balanced, non-comp-stomp, decided winner, not `incomplete`, and every
team has a known player. This is the same gate the rating model uses, so the ML
model is trained and evaluated on the same population we care about.

## Model architecture

A **DeepSets**-style encoder with three additive, individually-interpretable
contributions to the logit. Each can be ablated independently.

```
                 ┌─ per-player encoder (shared MLP) ─┐
player_id  ─emb─►│                                    │
general    ─emb─►│  h_i = MLP([e_player ; e_general ; │ ── pool(sum over i) ──► team vector t
faction    ─emb─►│         e_faction ; e_map ;        │
(map)      ─emb─►│         numeric_i])                │
                 └────────────────────────────────────┘

logit(A vs B) =
     [ score(t_A) - score(t_B) ]          # (1) individual strength + player/general/map interactions
   + [ syn(A)     - syn(B)     ]          # (2) teammate synergy  (low-rank, symmetric within team)
   + matchup(A, B)                         # (3) cross-team general counter (skew-symmetric)

P(A wins) = sigmoid(logit)
```

### (1) Individual + interaction term — `score(t) = w·t + b`

`t = Σ_i h_i` (sum-pool → permutation invariant; sum, not mean, but teams are
balanced so the two teams have equal size and the bias cancels in the
difference). The per-player MLP makes the contribution non-linear in
player/general/map jointly, which is how player×general and player×map affinities
are captured. **Linear ablation:** drop the MLP (identity) and this term reduces
to a learned Bradley-Terry / openskill-equivalent — our capacity floor.

### (2) Teammate synergy — low-rank, symmetric

Give each player a small **synergy embedding** `u_i ∈ R^k`. Team synergy bonus:

```
syn(A) = Σ_{i<j in A} u_i · u_j  =  ½(‖Σ_i u_i‖² − Σ_i ‖u_i‖²)
```

Computed in closed form (no explicit pairwise loop), permutation invariant, and
captures the same "do these two over-perform together" signal as
`player_synergy.py`, but learned jointly. Zero for 1v1 (no teammates).

### (3) General matchup / counter — skew-symmetric

A learned general-vs-general advantage. Let `M` be a `G×G` parameter and define
`A_gg' = M − Mᵀ` (skew-symmetric ⇒ `A_gg' = −A_g'g`). Counter term:

```
matchup(A,B) = Σ_{i in A} Σ_{j in B} A[g_i, g_j]
```

Skew-symmetry makes this term **automatically antisymmetric** under team swap, so
the whole logit stays antisymmetric. This is the learned analogue of the pairwise
general win/loss table. (Optional low-rank player-vs-player counter term has the
same form with player synergy-style embeddings; off by default — too sparse.)

### Global bias (base rate) + calibration

Two pieces sit outside the antisymmetric core because they target log-loss, which
the antisymmetric head alone handles poorly on small data:

- **Global bias** — a single learned scalar added to the logit. `team_a` is the
  *lower team id*, and empirically wins ≠ 50% (≈42% in the data), a real
  host/spawn-side asymmetry the antisymmetric head cannot express. Without it the
  model predicts ~50/50 and *loses* the free accuracy "always pick team_b" gets.
  It is excluded from weight decay so it can actually reach the base-rate logit.
- **Temperature scaling** — a single post-hoc scalar `T` (logit → logit/`T`) fit
  by minimising NLL on a **held-out tail of the train set** (leak-free vs dev).
  An accurate-but-overconfident net (good AUC, bad log-loss) is the textbook case
  for this; it lowers log-loss/Brier without changing the ranking. Stored in
  `calibration.json` and applied at inference (`OutcomeModel.calibrated_logit`).

Together with near-zero initialisation (so the initial logit ≈ 0 ⇒ loss ≈ ln 2,
rather than the large logits the quadratic synergy term produced under default
init) these are what move the model from "ranks fine but wildly overconfident" to
calibrated.

### Multi-team (FFA-balanced, num_teams > 2)

Replace the 2-team `sigmoid(s_A − s_B)` with a **softmax / Plackett-Luce** over
per-team scores `s_T = score(t_T) + syn(T) + Σ_{U≠T} matchup(T,U)`. v1 trains and
evaluates on 2-team games (the overwhelming majority); the head is written to
generalise so multi-team can be switched on later.

### Why this shape

- It is **interpretable**: each learned piece maps onto an analysis the repo
  already exposes (ratings, synergy, matchups), so we can sanity-check learned
  parameters against existing dashboards.
- It is **heavily regularisable** (small embeddings, weight decay, dropout in the
  MLP), which matters because the dataset is small (a tight community, thousands
  of games, dozens of regular players) — overfitting is the dominant risk.
- It **degrades to openskill** via ablation, giving an honest capacity floor.

### Hyperparameters (starting point)

`emb_player=16, emb_general=8, emb_faction=4, emb_map=8, synergy_k=8`,
per-player MLP `[64, 32]` with dropout 0.1, AdamW `lr=3e-3 weight_decay=1e-3`,
cosine schedule, batch size 256, early-stop on val log-loss. All in
`ml/config.py`; tuned by sweeping on the dev split.

## Training, evaluation, and splits

### Snapshot → split → train

1. **Snapshot** (`ml/snapshot.py`): pull all ratable competitive matches from the
   DB via `DATABASE_URL`, write a *versioned, immutable* `snapshot-<date>.jsonl.gz`
   plus a `manifest.json` (git SHA, row count, filter params, schema version).
   Training never touches the live DB — it reads a frozen snapshot for
   reproducibility.
2. **Split** (`ml/split.py`): split **by match** into train/dev. Two modes:
   - `temporal` (default): train on older games, dev on the most recent N% — the
     honest "can it predict the future" measure, and what we report.
     - `random`: stratified random — measures raw capacity / overfitting gap.
   The **vocab is frozen from the train split only**; players/maps unseen in
   train map to `UNK` at dev time (mirrors production, where new players appear).
3. **Train** (`ml/train.py`): PyTorch + **PyTorch Lightning** `LightningModule` /
   `Trainer(accelerator="auto")` → uses the GPU automatically. BCE-with-logits
   primary loss (+ down-weighted aux MSE heads when enabled). Saves the best
   checkpoint and the vocab JSON together as a self-contained bundle.

### Baselines (must beat, in order)

1. coin flip (log-loss = ln 2 ≈ 0.693);
2. **openskill `predict_win`** from `player_rating.py` evaluated on the same dev
   matches — the real bar;
3. logistic regression on the openskill rating difference;
4. our model (linear ablation, then full).

### Metrics

Log-loss (primary), accuracy, ROC-AUC, and **calibration** (Brier score +
reliability curve) — a win-probability model that isn't calibrated is misleading
even if its accuracy is fine.

### GPU train / CPU infer

- Train on GPU; checkpoint is device-agnostic.
- `ml/predict.py` loads with `map_location="cpu"`, reads the frozen vocab, accepts
  a match spec (players/teams/generals/map), and returns `P(team wins)` plus the
  decomposition into the three additive terms (strength / synergy / matchup) for
  explainability. Model is small enough that CPU latency is sub-millisecond.

## Dependencies & layout

ML deps (`torch`, `lightning`, `torchmetrics`, `scikit-learn`, `pandas`,
`pyarrow`) live in a **non-default `ml` dependency-group** in `pyproject.toml`, so
they are *never* installed into the production app (Heroku installs only
`[project.dependencies]`). Install locally with `uv sync --group ml`.

All ML code lives under `ml/`:

```
ml/
  model_design.md   # this file
  README.md         # how to run the pipeline
  config.py         # dataclass hyperparameters / paths
  snapshot.py       # DB -> frozen snapshot + manifest
  split.py          # snapshot -> train/dev (+ frozen vocab)
  features.py       # MatchInfo -> encoded tensors; vocab
  dataset.py        # torch Dataset / collate / DataModule
  model.py          # DeepSet+synergy+matchup model + LightningModule
  train.py          # training CLI (GPU)
  predict.py        # CPU inference + baseline/metric harness
  data/             # snapshots, splits, checkpoints (git-ignored)
```

Run order:

```
uv sync --group ml
uv run python -m ml.snapshot                  # writes ml/data/snapshot-<date>.jsonl.gz
uv run python -m ml.split  ml/data/snapshot-<date>.jsonl.gz   # writes train/dev + vocab
uv run python -m ml.train  ml/data/split-<date>/             # trains, writes checkpoint bundle
uv run python -m ml.predict ml/data/split-<date>/ --eval     # baselines + metrics on dev
```
