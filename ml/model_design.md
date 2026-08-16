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

Snapshot membership is `ml.snapshot.is_training_match`, which today is exactly
`player_rating.is_ratable_team_game`: competitive, balanced, non-comp-stomp,
decided winner, not `incomplete`, every team has a known player — **team games
plus tournament 1v1s**. It stays a separate name because there is no rule
saying the model must train on precisely the games that move a rating.

A bracket 1v1 is a real result between two people and the only place the model
sees a player's strength with no teammates confounding it. Casual 1v1s are
excluded, which was a measured decision, not an assumption:

| training set | 1v1s | logloss | acc | auc | ρ vs openskill |
|---|---|---|---|---|---|
| tournament 1v1s only | 15 | **0.6890** | **0.539** | **0.556** | +0.81 |
| \+ casual, minus the top pairing | 102 | 0.6908 | 0.522 | 0.538 | **+0.89** |
| \+ all casual | 227 | 0.6954 | 0.500 | 0.517 | +0.84 |

All three were scored on the **identical** 178-game held-out team dev set (the
temporal cut is over non-1v1 games, so adding 1v1s to train leaves dev
byte-identical — that is what makes the rows comparable). Every batch of casual
1v1s costs team-game accuracy, monotonically; the full set pushes logloss past
coin-flip (0.6931) and AUC to near-random. Consistent across all 30 bootstrap
replicates (median val_loss 0.6927 / 0.6925 / 0.6932).

Why: the 1v1 corpus is pathologically concentrated. Of 227 competitive 1v1s,
**125 are one pairing (CoreDawg vs Syn, 115–10)** — the next largest is 18, and
7 of the 21 pairings are a single day's session. The damage is *not* a distorted
strength estimate for the pair (a same-general probe moved CoreDawg +0.6pp, and
the spread across players narrowed); it is dilution — 16% off-distribution data
flattening the signal. Excluding that one pairing recovered most of it and gave
the best agreement with openskill's ordering, but still did not beat
tournament-only on the headline metric, so the simpler rule won.

Worth re-measuring when the 1v1 population changes shape — another bracket, or
casual play that spreads across more pairings. To reproduce: widen
`is_training_match` to accept 1v1s passing `filter_for_rating` +
`competitive_game_filter`, snapshot to its own `--out-dir`, and score against
`ml/data/split-<date>-temporal/dev.jsonl.gz`.

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

1. **Snapshot** (`ml/snapshot.py`): pull every match passing `is_training_match`
   (ratable team games + tournament 1v1s) from the
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
   **Tournament 1v1s are routed into train regardless of date** (`--holdout-1v1`
   opts out). They're the newest games in the snapshot, so a plain temporal cut
   held out all 15 of them: the model saw no 1v1 at all and `1v1` never entered
   the train-frozen vocab, so serving one fell back to the UNK format embedding.
   15 games can't measure 1v1 skill in a dev set either, so they buy more as
   training signal. The dev fraction applies to the games that *can* land in dev,
   so this grows train rather than shrinking dev.
3. **Train** (`ml/train.py`): PyTorch + **PyTorch Lightning** `LightningModule` /
   `Trainer(accelerator="auto")` → uses the GPU automatically. BCE-with-logits
   primary loss (+ down-weighted aux MSE heads when enabled). Saves the best
   checkpoint and the vocab JSON together as a self-contained bundle.

### Rolling-origin evaluation — the protocol we report

**A single dev slice cannot measure this model, and the numbers it gives are not
reproducible.** The temporal split leaves ~178 dev games; the bootstrap 95% CI on
AUC over that slice spans **0.470–0.637**, so it cannot separate the model from a
coin flip. Worse, per-block AUC ranges from 0.54 to 0.79 across the corpus — which
fortnight the cut lands on moves the headline number more than any modelling
change does, and the most recent block (the one `ml.split` hands you) happens to
be one of the bad ones.

`ml/rolling_eval.py` walks the cut across the snapshot instead — train up to the
cut with the vocab frozen there, predict the block immediately after, pool every
block — for 420 test games out of the same 1,205-match corpus. Same data, 2.4×
the measurement, and no single fortnight dominates. It is what step 4c of the
README runs, and what any claim about model quality should quote:

| protocol | test games | log-loss | acc | AUC |
|---|---|---|---|---|
| single dev slice (what `ml.predict --eval` gives) | 178 | 0.6890 | 0.539 | **0.556** |
| rolling origin, 5 cuts × 3 seeds — single model | 420 | 0.6522 | 0.623 | 0.688 |
| rolling origin — 3-seed bagged | 420 | **0.6342** | 0.629 | **0.698** |
| rolling origin — openskill on the same blocks | 420 | 0.7486 | 0.595 | 0.646 |

The model is a good deal better than the number in the old write-up said; the old
number was a measurement artifact, not a model failure.

### Recency weighting

Training games are down-weighted by age, `w = 0.5 ** (age_days/half_life)`,
anchored to the newest game *in the training block* and renormalised to mean 1.0
(`features.recency_weighted`; `TrainConfig.recency_half_life_days`, default
**730 days**). Dev is always left uniform — `val_loss` drives early stopping and
cross-run comparison, so it has to keep meaning the same thing.

Players drift: the median regular's yearly win rate moves ~10 points, and Skip's
went 31% → 45% across five years. A four-year-old game is evidence about a
different player. Swept under rolling origin (bagged, 420 games):

| half-life | log-loss | Brier | AUC |
|---|---|---|---|
| none (uniform) | 0.6359 | 0.2224 | 0.687 |
| 1095 d | 0.6356 | 0.2224 | 0.692 |
| **730 d** | **0.6342** | **0.2215** | 0.698 |
| 545 d | 0.6381 | 0.2222 | **0.701** |
| 365 d | 0.6423 | 0.2231 | 0.699 |

730d wins log-loss (the primary metric) and Brier; 365–545d rank a hair higher on
AUC but calibrate worse. The whole effect is ~+0.011 AUC — worth more than the
next 16,000 matches would buy (see the data-budget note below), and free.

### How much more data would help (measured, 2026-08)

Asked directly, with the learning curve run under the rolling protocol:

- **The curve is saturating.** AUC by training size: 80→0.572, 300→0.640,
  700→0.663, 1118→0.666. A saturating fit `auc(n) = 0.678 − 4.62·n^-0.85`
  (χ²=3.7, 4 dof) puts this feature set's asymptote at **0.678** — the next
  +0.01 AUC needs ~17,800 matches, about 23 years at the current 59/month.
- **There is a ceiling, and we are near it.** A beta-binomial fit over 255
  repeated fixtures gives sd(true p) = 0.234 (CI 0.197–0.260) → a perfect
  forecaster scores AUC ≈ 0.77. A model-free leave-one-out fixture oracle reaches
  0.725. Roughly a quarter of outcomes are decided by things no pre-game feature
  sees.
- **Capacity, not volume, is the live constraint.** 6,859 parameters against
  1,027 training labels; a 31-parameter logistic (signed player indicators +
  signed general counts) scores AUC 0.666 under the identical protocol.
- **The 144-cell general matrix is not supported.** Adding general-vs-general
  pair terms moves rolling AUC 0.667 → 0.644 and log-loss 0.643 → 0.700 — pure
  overfitting. General *main* effects are worth +0.0164 AUC (95% CI −0.0006 to
  +0.0338; they beat a shuffled-generals control at 0.6445 ± 0.0073), so they are
  probably real but not yet significant: confirming them needs ~990 test games,
  i.e. a corpus around 6,600. Resolving a 5pp edge in every cell needs ~782 games
  *per cell* → ~12,500 matches. Treat `predict_faction_matchup` output as
  illustrative until then.

### Baselines (must beat, in order)

1. coin flip (log-loss = ln 2 ≈ 0.693);
2. **openskill `predict_win`** from `player_rating.py` evaluated on the same dev
   matches — the real bar;
3. logistic regression on the openskill rating difference;
4. our model (linear ablation, then full).

### Metrics

Log-loss (primary), accuracy, ROC-AUC, and **calibration** (Brier score +
reliability curve) — a win-probability model that isn't calibrated is misleading
even if its accuracy is fine. Report them from `ml.rolling_eval`, not from a
single dev slice; at this corpus size the slice-to-slice spread is larger than
any effect we are trying to measure.

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
  predict.py        # CPU inference + baseline/metric harness (single split)
  rolling_eval.py   # rolling-origin evaluation - the numbers we report
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
