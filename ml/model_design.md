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

## The corpus (measured 2026-08-28, snapshot-20260828)

Read this before proposing any architecture. Almost every design question below
is decided by it.

| | |
|---|---|
| trainable matches | **1,251** (2022-01-01 .. 2026-08-26), 1,249 usable 2-team games |
| **distinct players** | **17**, of whom 15 played in the last 365 days |
| player concentration | the top 10 fill 90% of all slots; nobody has fewer than 33 games |
| formats | 2v2 547, 3v3 494, 4v4 176, 1v1 32 (all tournament), 2v2v2 2 |
| maps | 187 distinct, 59 of them played exactly once; top 10 maps = 29% of games |
| games with a CPU slot | 214 (17%) |
| repeated fixtures | 444 distinct team-vs-team fixtures; 1,070 games sit in one seen 2+ times |
| arrival rate | ~60/month over the last year |

**Seventeen players.** That single number governs everything. The task is
"estimate 17 drifting strengths and whatever interactions the data can carry",
and the data can carry very few: of 107 teammate pairs that ever occur, 52 have
under 30 games; of 115 opponent pairs, 55 do. There are ~1,250 labels against
the served model's ~6,900 parameters, and its two largest blocks - the per-map
embedding (187 x 8) and the per-player MLP (~4,700) - are the two the corpus
supports least.

**Player skill converges over time, and that makes the corpus *harder*, not
easier.** Fitting the 17-parameter Bradley-Terry model separately on each half
of the corpus, the weakest players gain the most (Syn +1.37, Skip +0.77,
WildCard +0.58 in logit units) and the spread of strengths narrows (sd
1.07 -> 1.00). Held-out log-loss follows: the first three 120-game blocks average
0.615, the last three 0.672. A model that looks better because it was scored on
2025 games is not better.

**Per-block variance dwarfs every modelling effect.** Scoring the same
17-parameter model on consecutive 120-game blocks gives AUC from 0.573
(2026-05..07) to 0.805 (2025-12..2026-01) and log-loss from 0.513 to 0.689. The
sd of a *paired* per-game log-loss difference between two nearby models is ~0.10,
so at the 435 games the rolling protocol pools, the 95% interval on any
difference is about +-0.011, and at 812 games about +-0.007. **Anything smaller
than that is not a result.** Several things in this document that used to read
as findings are inside that band.

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

**openskill is also a much lower bar than it looks, because its probabilities
are not calibrated.** Scored as-of on 812 rolling test games, its stated
favourites win far less often than it says:

| openskill says the favourite has | games | favourite actually won |
|---|---|---|
| 50-60% | 172 | 55.8% |
| 60-70% | 192 | 47.4% |
| 70-80% | 118 | 61.9% |
| 80-90% | 131 | 63.4% |
| 90-97% | 93 | 62.4% |
| 97-100% | 106 | 82.1% |

Its log-loss is **0.806 — worse than a coin flip's 0.693** — while its AUC is a
respectable 0.642, the signature of a model that ranks fine and states wildly
overconfident numbers. A single fitted temperature drops it to 0.679 without
touching the ranking. "Beats openskill on log-loss" is therefore nearly free and
proves nothing; see `ml/baselines.py` for the bar that does bite.

This matters outside the model, too. `player_rating.GameUpset.favored_win_prob`
/ `winner_win_prob` are this same `predict_win` output, and they are what the
public **🐍 Biggest Upset** superlative and the game-night highlight print as
"X% to win" (the superlative to two decimal places). Read off the last row of the
table: when openskill puts a side at 97-100%, the *other* side wins 17.9% of the
time — so a card reading "2.5% to win" is describing something closer to a 1-in-6
shot. The overconfidence is structural, not an artifact of scoring as-of: it
comes from the spread of `mu` being large relative to `beta`, and the app's
version uses the *converged* ratings, which are sharper still.

Nothing here changes those surfaces. `predict_win` also drives the rating update
(`_compute_surprise_uncertainty`) and `create_teams`, so rescaling it is not a
display-only change and is not a call to make inside an ML write-up. But the
number as published is not a probability, and if a calibrated one is wanted the
ML ensemble already produces it.

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

Everything is derived from `api_types.MatchInfo` (see `radarvan/api_types/matches.py`).
All player names are alias-resolved with `player_ids.resolve_player_name` *before*
vocab lookup — clients/replays use in-game aliases.

### Per-player categorical features (embedded)

| feature | cardinality | notes |
|---|---|---|
| `player_id` | ~ #known players + `UNK` | from `player_ids.PLAYER_NAMES`; anyone not in the training vocab → `UNK` |
| `general` | 12 + `UNK` | `api_types.General` (USA/AIR/LASER/SUPER, CHINA/NUKE/TANK/INFANTRY, GLA/TOXIN/STEALTH/DEMO) |
| `faction` | 3 + `UNK` | derived: `general // 4` → USA / China / GLA. Redundant with general but a useful coarse fallback for rare general×player combos |
| `starting_position` | small int + `UNK` | optional; map-relative spawn, stored 1-based (`player_role.start_position_from_header` adds 1 to the replay's 0-based value, so a lobby "random" slot lands on 0). 27% of games have at least one such slot, so it is **off by default** |

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

### Features that were tried and do not help (2026-08-28)

All scored on the 17-parameter logistic under both rolling protocols, so a real
effect had two chances to show up consistently. None did, and the corpus section
explains why: each of these asks the data for interaction structure it does not
have.

| candidate | what it is | result |
|---|---|---|
| teammate-pair indicators | explicit synergy, 107 signed columns | **much worse** (0.636 → 0.662) |
| opponent-pair indicators | explicit head-to-head, 115 signed columns | neutral (0.636 → 0.636) |
| general main effects | 12 signed general counts | neutral / slightly worse |
| player × faction | 51 columns, "who is good as GLA" | worse (0.646) |
| player × time trend | a per-player linear drift term | worse (0.643) |
| as-of fixture record | shrunk log-odds of this exact fixture's history | +0.004 dense, 0 on cuts |
| as-of form | team mean of each player's last-20-games win rate | +0.003 cuts, 0 dense |
| session state | games played tonight; days since last game | neutral to worse |
| **spawn geometry** | from `MapData.player_starts` + `starting_position`: teammate spawn spread, nearest-enemy distance, centrality, supply/oil within reach | +0.007 AUC on cuts, −0.005 on dense — inconsistent, i.e. noise |

The spawn-geometry one is the most interesting failure, because the feature is
physically real and the data is there (916 of 1,249 games have every participant's
spawn resolved *and* map geometry; the other 333 lose it to lobby "random"
positions, which the replay header records as −1). It still moves nothing.

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

(All four rows below are on the leaky protocol; see "The measurement bug", and
the re-measurement at the end of this section.)

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

**Re-measured 2026-08-28 — the evidence for the rule no longer holds.** The 1v1
population did change shape: tournament 1v1s went 15 → 32, casual 1v1s 227 → 217
across 22 pairings, and the CoreDawg-vs-Syn concentration is now 124 of 217
rather than 125 of 227. Adding casual 1v1s to *train* only (the test blocks stay
byte-identical team games, so the rows are paired), scored with the 17-parameter
logistic — the cheapest thing that responds to the training set, and the model
whose numbers are not confounded by early stopping:

| training set | 435-game cuts | 812-game dense |
|---|---|---|
| tournament 1v1s only *(the rule)* | 0.6368 / AUC 0.667 | 0.6359 / AUC 0.667 |
| \+ all casual 1v1s | 0.6338 / AUC 0.672 | 0.6349 / AUC 0.670 |
| \+ casual minus the top pairing | **0.6334** / AUC 0.672 | **0.6343** / AUC 0.671 |

Including them is now very slightly *positive*, consistently in both protocols —
and by 0.001–0.003 log-loss, i.e. inside the noise band either way. The original
finding was measured on one 178-game dev slice with the leaky model; it is not
reproducible under this protocol. **The filter is left as it is** — there is no
significant gain to bank — but the "measured decision" above should be read as
"measured once, on a protocol we no longer trust, and no longer supported."

Two other hygiene questions, same protocol, same answer: dropping the 214
CPU-containing games from training moves nothing (0.6359 → 0.6365), and games
without a CPU are simply easier to predict (0.6256 vs 0.6359), which is a property
of the test set rather than of the filter.

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

### Team-size normalisation (`size_norm`, on by default)

Every additive term is divided by the number of things pooled: the score by
`|team|`, the synergy by the teammate-pair count, the matchup by `|A|·|B|`. The
teams in a match are balanced, so this cancels *within* a match — but it does not
cancel *across* formats. With plain sum-pooling a 4v4's logit carries four times
a 1v1's strength spread purely from the pooling, and the single shared
temperature cannot calibrate both. It is the largest single modelling
improvement measured here:

| pooling | log-loss | acc | AUC | Brier |
|---|---|---|---|---|
| sum (the old default) | 0.6717 | 0.618 | 0.634 | 0.2388 |
| **mean (`size_norm`)** | **0.6543** | 0.618 | **0.667** | **0.2300** |

435 pooled rolling test games, 3 seeds bagged, leak-free validation. +0.033 AUC
and −0.017 log-loss — and the same effect shows up in the plain logistic (0.6536
sum vs 0.6368 mean), which is what prompted looking for it in the net. It is the
only configuration change measured here that survives a paired bootstrap: against
`bt_logistic`, sum-pooling loses by +0.0352 log-loss [+0.0042, +0.0649] while
`size_norm` closes to +0.0177 [−0.0049, +0.0409].

### (1) Individual + interaction term — `score(t) = w·t + b`

`t = Σ_i h_i` (permutation invariant; averaged rather than summed when
`size_norm` is on, see above). The per-player MLP makes the contribution non-linear in
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
  *lower team id*, and over the whole corpus it wins only 41.2%. It is excluded
  from weight decay so it can actually reach the base-rate logit. **It is off by
  default, and the reason is that the asymmetry is disappearing**: by year the
  team_a win rate runs 0.33 (2023), 0.35 (2024), 0.43 (2025), 0.45 (2026), and
  over the last 200 games it is 0.495. Fitting it is fitting history. The
  `base_rate` baseline in `ml/baselines.py` confirms it out-of-sample — predicting
  the training block's own team_a rate scores log-loss 0.696 on the pooled rolling
  test set, *worse* than a coin flip's 0.693.
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

### What the corpus says about this shape (2026-08-28)

The three-term decomposition is still the right *interpretable* frame, and it is
still what `ml.predict --match-id` explains a prediction with. But measured
leak-free under the rolling protocol, none of the three terms is separable from
the others at this corpus size, and the whole net does not beat a 17-parameter
Bradley-Terry logistic on log-loss or Brier. Read the "Rolling-origin evaluation"
tables before adding capacity here: the model already has ~6,900 parameters for
~1,250 labels, and every extra term measured so far has come back inside the
noise band (synergy, matchup, map, the MLP itself) or outside it in the wrong
direction (the 144-cell general matrix; explicit teammate-pair indicators).

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
`ml/config.py`. Historically "tuned by sweeping on the dev split" — which, given
that early stopping also watched dev, means these values were chosen twice over
on the set that was then reported. Sweep on `ml.rolling_eval` instead, and treat
anything inside ±0.011 log-loss as untuned.

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
   **`dev.jsonl.gz` is never read during fitting**: `TrainConfig.val_frac` holds
   back the recent tail of train for early stopping and the temperature, and
   `refit_on_full` then refits on the whole split for the chosen epoch count. See
   "The measurement bug" below for what happens without this.

### The measurement bug (found and fixed 2026-08-28)

**Every rolling-origin number this document published before today was inflated,
because early stopping watched the set being scored.**

`ml.train` selects the best checkpoint and stops early on `val_loss`, and
`MatchDataModule.val_dataloader` returned `dev.jsonl.gz` — which in
`ml.rolling_eval` *is* the test block, and in a `split-*` directory *is* what
`ml.predict --eval` then reports. Choosing the checkpoint by its score on the
evaluation set is test-set model selection, and it was worth about **+0.06 AUC**.

The temperature fit was wrong in the opposite direction and for the opposite
reason: `_calibrate` used the last 20% of the *fit* block, i.e. games the weights
had already memorised. An overfit net looks perfectly calibrated on its own
training data, so the fit returned **T = 0.754** — making an already-overconfident
model *more* confident. Fitted on genuinely held-out games the same run asks for
**T = 1.77**. That is why the model out-ranked a 17-parameter logistic on AUC
while losing to it on log-loss.

Both are fixed by `TrainConfig.val_frac` (default 0.15): the most recent slice of
*train* is held out, early stopping and the temperature both use it, and
`dev.jsonl.gz` is never read during fitting. `tests/test_ml_validation_split.py`
asserts the property (val disjoint from fit and from dev, val ∪ fit == train, val
is the recent end) rather than a fixed size. `ml_win_prediction_over_time` had
the identical bug and carries the identical fix; its shipped ONNX predates it.

One visible consequence: on ~160 honest validation games the val curve is noisy
and early stopping now fires at **epoch 3-7** rather than the tens of epochs the
leaky setup ran for. That is the correct answer for this much data, not a bug —
but it does mean the served weights are barely trained, and a smoothed stopping
rule or a fixed epoch budget is a reasonable thing to try. It was not tried here
because the effect would have to exceed ±0.011 log-loss to be visible at all.

`TrainConfig.refit_on_full` (default on) buys back the games the holdout costs:
after early stopping picks an epoch count, the model is refit from scratch on the
whole train split for that many epochs, carrying the temperature fitted on the
holdout. Nothing but the epoch count crosses over.

### Rolling-origin evaluation — the protocol we report

**A single dev slice cannot measure this model, and the numbers it gives are not
reproducible.** The temporal split leaves ~180 dev games; per-block AUC ranges
from 0.57 to 0.81 across the corpus — which fortnight the cut lands on moves the
headline number more than any modelling change does.

`ml/rolling_eval.py` walks the cut across the snapshot instead — train up to the
cut with the vocab frozen there, predict the block immediately after, pool every
block — for 435 test games out of the 1,251-match corpus. It is what step 4c of
the README runs, and what any claim about model quality should quote.

All rows below: snapshot-20260828, 5 cuts × 3 seeds bagged, 435 pooled games.
Read them with the paired intervals underneath, not as a ranking — the ±0.011
figure quoted in the corpus section is what separates two *nearby* variants of
the same model; across model classes the predictions are less correlated and the
interval roughly doubles.

| | log-loss | acc | AUC | Brier |
|---|---|---|---|---|
| coin flip | 0.6931 | 0.561 | 0.500 | 0.2500 |
| base rate (train block's team_a rate) | 0.6893 | 0.561 | 0.532 | 0.2480 |
| openskill `predict_win` | 0.7935 | 0.607 | 0.639 | 0.2640 |
| **`bt_logistic` — 17 parameters** | **0.6368** | 0.614 | 0.667 | **0.2248** |
| model, as published (leaky val, sum-pool) | 0.6695 | 0.632 | *0.695* | 0.2273 |
| model, leak fixed, sum-pool | 0.6717 | 0.618 | 0.634 | 0.2388 |
| model, leak fixed, `size_norm` | 0.6543 | 0.618 | 0.667 | 0.2300 |
| model, leak fixed, `size_norm`, no synergy | 0.6505 | 0.621 | **0.671** | 0.2281 |

Read it in that order. Removing the leak costs the headline AUC 0.695 → 0.634;
team-size normalisation earns 0.634 → 0.667 back honestly, and the model's
log-loss ends up **better than the number it used to publish** (0.6543 vs 0.6695)
because the calibration is no longer fitted in-sample.

**And it still does not beat a 17-parameter logistic on anything.** Paired
bootstrap over the same 435 games, best fixed configuration vs `bt_logistic`:

| comparison | log-loss diff (95% CI) | AUC diff (95% CI) |
|---|---|---|
| model (fixed, no synergy) − `bt_logistic` | +0.0138 [−0.0090, +0.0367] | +0.0041 [−0.0322, +0.0408] |
| model (fixed, default) − `bt_logistic` | +0.0177 [−0.0049, +0.0409] | −0.0004 [−0.0341, +0.0351] |
| model (**as served before today**) − `bt_logistic` | **+0.0352 [+0.0042, +0.0649]** | −0.0333 [−0.0775, +0.0121] |

The first two intervals straddle zero: the net is *behind* on log-loss and level
on AUC, and neither gap is significant — the honest reading is "400× the
parameters buys nothing measurable". The third does not straddle zero: the
sum-pooling configuration that was in `ml_ensemble/` this morning was
**significantly worse** than 17 numbers, P(logistic better) = 0.99. That is the
one unambiguous result in this document.

None of this is a surprise given the corpus section above — it is the same
conclusion the data-budget note below reached from the other direction, and the
reason `ml/baselines.py` now ships that logistic as a first-class baseline rather
than a line in a to-do list.

#### The best predictor measured here is a blend

| | log-loss | acc | AUC | Brier |
|---|---|---|---|---|
| `bt_logistic` (17 params) | 0.6368 | 0.614 | 0.667 | 0.2248 |
| model, fixed (`size_norm`, no synergy, `refit_on_full`) | 0.6485 | 0.607 | 0.670 | 0.2270 |
| **mean of the two logits** | **0.6356** | 0.602 | **0.678** | **0.2230** |

Paired bootstrap against `bt_logistic` over the same 435 games: log-loss
−0.0011 [−0.0115, +0.0101] (P(better) = 0.58), AUC +0.0117 [−0.0060, +0.0289]
(P = 0.90). So the blend is the best row on three of four metrics and is *not*
significantly better than the logistic alone — but it is clearly better than
either the net alone or what production serves today.

The same test is the one place something *is* significant: the old sum-pooling
default loses to the 17-parameter logistic by +0.0352 log-loss [+0.0042,
+0.0649], P(logistic better) = 0.99.

**Serving the blend is the obvious next step and is deliberately not done here.**
It needs a second artifact next to the ONNX ensemble — 18 floats, the fitted
`bt_logistic` coefficients plus the player index — and a blend step in
`radarvan/ml_inference.py`. That is a production-architecture decision (two model
classes on the serving path) for a gain that is real against today's ensemble and
a wash against just serving the logistic; the measurement is recorded so the
decision can be made on evidence rather than repeated.

#### Config ablations, all leak-free, same 435 games

| variant | log-loss | acc | AUC |
|---|---|---|---|
| no synergy, `refit_on_full` | 0.6485 | 0.607 | 0.670 |
| no synergy | 0.6505 | 0.621 | 0.671 |
| no map, no synergy, no matchup ("lean") | 0.6520 | 0.618 | 0.664 |
| no map | 0.6526 | 0.611 | 0.664 |
| recency half-life 365d | 0.6530 | 0.602 | 0.656 |
| no MLP (linear floor) | 0.6540 | 0.589 | 0.648 |
| **default (`size_norm`, everything on)** | 0.6543 | 0.618 | 0.667 |
| no matchup | 0.6548 | 0.605 | 0.667 |
| sum pooling | 0.6717 | 0.618 | 0.634 |

Every row except the last is inside ±0.011 of every other row. **Dropping synergy
looks best and is not significant**, so it stays on by default; the same goes for
dropping the map and for the half-life. Only `size_norm` separates itself. Do not
read this table as a ranking — read it as "one knob matters and the rest are
noise at this corpus size".

### Recency weighting

Training games are down-weighted by age, `w = 0.5 ** (age_days/half_life)`,
anchored to the newest game *in the training block* and renormalised to mean 1.0
(`features.recency_weighted`; `TrainConfig.recency_half_life_days`, default
**730 days**). Dev is always left uniform — `val_loss` drives early stopping and
cross-run comparison, so it has to keep meaning the same thing.

Players drift: the median regular's yearly win rate moves ~10 points, and Skip's
went 31% → 45% across five years. A four-year-old game is evidence about a
different player. Swept under rolling origin (bagged, 420 games, **on the leaky
protocol** — see "The measurement bug"; every row here is inflated by the same
amount, so the *ordering* is what the table was ever claiming):

| half-life | log-loss | Brier | AUC |
|---|---|---|---|
| none (uniform) | 0.6359 | 0.2224 | 0.687 |
| 1095 d | 0.6356 | 0.2224 | 0.692 |
| **730 d** | **0.6342** | **0.2215** | 0.698 |
| 545 d | 0.6381 | 0.2222 | **0.701** |
| 365 d | 0.6423 | 0.2231 | 0.699 |

730d wins log-loss (the primary metric) and Brier; 365–545d rank a hair higher on
AUC but calibrate worse.

**Re-measured 2026-08-28: that sweep does not resolve.** Its whole spread is
0.0081 log-loss, and the 95% interval on a paired difference at 812 test games is
±0.007 — the table was reading noise. Swept again on the 17-parameter logistic
over 812 rolling test games, half-lives from 120d to ∞ span 0.6354 (270d) to
0.6428 (uniform), and the ordering *flips* between the first and second halves of
the test set: the recent half prefers the long half-lives the early half rejects.
Uniform weighting is the only setting clearly worse than the rest. The default
stays 730d for continuity, not because it won.

### What "better" can even mean here (measured 2026-08-28)

A perfect pre-game forecaster would still look mediocre, so absolute accuracy is
the wrong yardstick. Fitting a beta-binomial over the 265 fixtures seen twice or
more gives the spread of *true* per-fixture win probabilities: Beta(2.10, 1.72),
sd(p) = 0.227. From that distribution:

| | value |
|---|---|
| irreducible log-loss (a forecaster that knows every true p) | **0.574** |
| irreducible Brier | 0.196 |
| accuracy ceiling | **69.5%** |
| coin flip log-loss | 0.693 |

So the entire attainable range is 0.119 nats wide, and a *skill score* — how much
of the gap between the coin flip and the ceiling a model closes — is the honest
summary:

| | log-loss | skill score |
|---|---|---|
| openskill `predict_win` | 0.7935 | **−84%** (worse than a coin flip) |
| model, as published (leaky) | 0.6695 | 20% |
| model, leak fixed, sum-pool | 0.6717 | 18% |
| model, leak fixed, `size_norm` | 0.6543 | 33% |
| **`bt_logistic`, 17 parameters** | **0.6368** | **47%** |
| perfect forecaster | 0.5742 | 100% |

62% accuracy against a 69.5% ceiling is most of what is there. Roughly a quarter
of these games are decided by things no pre-game feature can see, and about
another quarter by structure this corpus is too small to estimate.

### How much more data would help (measured, 2026-08)

Asked directly, with the learning curve run under the rolling protocol:

- **The curve is saturating.** AUC by training size: 80→0.572, 300→0.640,
  700→0.663, 1118→0.666. A saturating fit `auc(n) = 0.678 − 4.62·n^-0.85`
  (χ²=3.7, 4 dof) puts this feature set's asymptote at **0.678** — the next
  +0.01 AUC needs ~17,800 matches, about 23 years at the current 59/month.
- **There is a ceiling, and we are near it.** A beta-binomial fit over 255
  repeated fixtures gives sd(true p) = 0.234 (CI 0.197–0.260) → a perfect
  forecaster scores AUC ≈ 0.77. (Re-fitted 2026-08-28 over 265 repeated fixtures:
  Beta(2.10, 1.72), sd = 0.227, AUC ceiling 0.763 — unchanged in substance.) A
  model-free leave-one-out fixture oracle reaches
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

All four are implemented and scored automatically by `ml.predict --eval` and
`ml.rolling_eval`; three of them live in `ml/baselines.py` (torch-free).

1. **coin flip** — log-loss ln 2 ≈ 0.693.
2. **base rate** — the training block's own team_a win rate. Currently *loses* to
   the coin flip out-of-sample (0.696); see the global-bias note above.
3. **openskill `predict_win`** — ranks well (AUC 0.639) and is badly calibrated
   (log-loss 0.794). Beating it on log-loss is free.
4. **`bt_logistic`** — the bar that bites. An L2-penalised, recency-weighted
   Bradley-Terry fit: one signed indicator per player, mean-pooled over the team,
   **17 parameters on this corpus**. No generals, no map, no synergy, no
   interactions. It is what "who is on which team" alone is worth, and the
   400x larger model has to justify itself against it.

For a long time this list was aspirational — only 1 and 3 were ever computed, and
3 is the weak one. That is how a model that does not clear its own capacity floor
went unnoticed.

### Metrics

Log-loss (primary), accuracy, ROC-AUC, and **calibration** (Brier score +
reliability curve) — a win-probability model that isn't calibrated is misleading
even if its accuracy is fine. Report them from `ml.rolling_eval`, not from a
single dev slice; at this corpus size the slice-to-slice spread is larger than
any effect we are trying to measure.

**Quote an interval, not a point.** The paired per-game log-loss difference
between two nearby models has sd ≈ 0.10 here, so 435 pooled games resolve
±0.011 and 812 resolve ±0.007. Report the paired bootstrap on the difference
(`log_loss` and `auc`), not two point estimates side by side — most of the tables
in this document's history were four-decimal readings of noise, and the one
genuinely large effect (sum-pooling vs `size_norm`) was hiding behind them the
whole time. A skill score against the 0.574 irreducible log-loss is the honest
way to say how good a number is.

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
  baselines.py      # base rate + the 17-parameter Bradley-Terry logistic (torch-free)
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
