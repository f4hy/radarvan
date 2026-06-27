# Player Synergy Methodology

## Goal

For every pair of players, decide whether they win **more or less often when they
are teammates than their individual ratings alone would predict**. We already
have an OpenSkill (Plackett–Luce) rating per player and, for every team game, a
model‑predicted win probability plus the actual result. Synergy is the
*systematic deviation* of the result from that prediction that is attributable to
a specific pair being on the same team.

The output we want is one number per pair: positive ⇒ the pair over‑performs
their combined ratings (chemistry), negative ⇒ they under‑perform (anti‑synergy),
zero ⇒ they play exactly as their ratings say.

## What we already have to build on

`radarvan/player_rating.py` runs OpenSkill over all competitive team games
(`compute_player_ratings`). For a single game it does:

```python
pteams     = [[rating(p) for p in team] for team in teams]   # two teams
prediction = model.predict_win(teams=pteams)                 # [p_A, p_B], sums to 1
```

So for any game we can reconstruct the model's pre‑game win probability for each
team from the **converged** ratings. The actual winner is `game.winning_team`.
That gives us, per game, a `(predicted_prob, outcome)` pair — exactly the raw
material for measuring synergy as *residual* (observed − expected).

## Models considered

### 1. Mean residual per pair (naive)

For each game, residual `r = outcome − predicted_prob` for the winning/losing
team. Assign that residual to every teammate pair in the game and average per
pair:

```
synergy(i, j) = mean over games where i,j are teammates of (outcome − predicted_prob)
```

* **Pro:** trivial, directly interpretable as "win % above expectation."
* **Con (fatal for 3v3/4v4):** in a 3‑ or 4‑player team the single shared
  outcome is copied onto *every* pair, so the three pairs in a 3v3 team are
  perfectly correlated. If player A simply out‑performs their rating, **every**
  pair containing A looks synergistic — the method cannot separate an individual
  rating lag from genuine pair chemistry. No regularization, so a pair with two
  games can show a huge spurious effect.

### 2. Regularized logistic regression with pairwise interaction terms  ✅ chosen

Treat each game as one Bernoulli trial. Orient each game so "team A" is the
lower team id; let `y = 1` if team A won. Use the rating model's log‑odds as a
fixed **offset** (we are *not* re‑estimating individual skill, we are explaining
what's left over):

```
offset = logit(p_A)                       # from predict_win on converged ratings
```

Then model the residual log‑odds with **player main effects** and **pairwise
interaction terms**:

```
logit P(A wins) = offset
                + Σ_{i in A} m_i      − Σ_{i in B} m_i           (main effects)
                + Σ_{i<j in A} s_ij   − Σ_{i<j in B} s_ij        (pair synergies)
```

Each feature is signed `+1` if the player/pair is on team A, `−1` if on team B,
`0` otherwise. `s_ij` is the synergy coefficient we want: the extra log‑odds the
team gets *purely because i and j are paired*, on top of (a) what their ratings
predict and (b) how each of them individually deviates from their rating.

Fit by maximizing the L2‑penalized Bernoulli log‑likelihood (ridge logistic
regression):

```
maximize  Σ_g [ y_g log σ(η_g) + (1−y_g) log(1−σ(η_g)) ]
          − (λ_main/2) Σ m_i²  − (λ_pair/2) Σ s_ij²
```

* **Why main effects matter.** Suppose A's OpenSkill rating lags their true
  skill. Without main effects the optimizer can only explain A's
  over‑performance by inflating *all* of A's pair coefficients — re‑creating the
  exact confound that sinks Model 1. The explicit `m_A` term absorbs that
  individual offset in **one** lightly‑penalized parameter, leaving `s_ij` to
  capture only the part that is specific to the *pair*. This is the crucial
  difference from the naive residual.

* **Why ridge.** Most pairs appear in few games. The quadratic penalty shrinks
  thinly‑observed pairs toward 0 (no synergy is the prior), and shrinks them
  *more* the less evidence there is. A pair seen 40 times barely moves; a pair
  seen twice is pulled almost all the way back to 0. The shrinkage factor for a
  pair seen in `g` games is roughly `I/(I+λ)` with Fisher information
  `I ≈ Σ p(1−p) ≤ 0.25·g`, so `λ_pair` directly sets "how many games before I
  believe a pair effect."

* **Identifiability / overlap.** Because all pairs and main effects are fit
  *jointly*, overlapping pairs in a 3v3/4v4 are properly disentangled — the fit
  attributes the shared outcome to whichever combination of main and pair terms
  best explains *all* games at once, not just the one in front of it. The
  arbitrary A/B orientation is symmetric (flipping a game flips both `y` and the
  offset and all feature signs), so no intercept is needed.

* **Uncertainty for free.** The inverse of the penalized Hessian at the optimum
  is a Laplace‑approximate covariance. Its diagonal gives an approximate standard
  error per pair, hence a z‑score `s_ij / se_ij` to separate "real" synergy from
  noise.

* **Cost:** a design matrix and a few Newton steps. With ~20 rated players there
  are ≤190 pairs and a few thousand games — milliseconds in pure NumPy. No new
  dependency (scipy/sklearn are *not* installed; Newton–Raphson IRLS in NumPy is
  enough and matches the lightweight style of the existing rating code).

### 3. Empirical‑Bayes shrinkage of the Model‑1 residual

Model 1 plus normal–normal shrinkage toward 0 by sample size. Fixes the small
sample problem but **not** the overlapping‑pair / individual‑lag confound, which
is the more important defect. Strictly dominated by Model 2.

### 4. Pair "rating" baked into the skill model (TrueSkill‑style factors)

Add a latent factor per pair inside the Plackett–Luce rating update itself.
Most principled in theory, but it means forking the rating model, makes ratings
and synergy circularly dependent, and is far heavier than the question warrants.
Overkill.

## Decision

**Model 2 — ridge logistic regression with player main effects + pairwise
interaction terms over the rating model's log‑odds offset.** It is the only
candidate that simultaneously (a) separates genuine pair chemistry from an
individual's rating lag, (b) disentangles the overlapping pairs inherent to
3v3/4v4, and (c) regularizes the long tail of rarely‑seen pairs while giving a
usable uncertainty estimate — all without new dependencies.

## Implementation summary

`radarvan/player_synergy.py`:

1. `compute_player_ratings(games)` (cached) → converged `NamedRating` per player.
2. Replay the same filtered competitive team games; for each, build the two
   teams, look up ratings, compute `offset = logit(p_A)` via `model.predict_win`,
   record `y`, the participating players, and the participating pairs.
3. Assemble the signed design matrix `X` (main‑effect columns + pair columns),
   the `offset` vector and `y`.
4. Fit ridge logistic regression by Newton–Raphson (IRLS) with separate `λ_main`
   and `λ_pair`. Standard errors from the inverse penalized Hessian.
5. Emit one record per pair: `synergy` (log‑odds), `win_prob_delta`
   (`σ(synergy) − 0.5`, the effect at an even matchup), `games_together`,
   `wins_together`, `expected_wins` (Σ predicted prob), `std_error`, `z_score`.
   Pairs below a `min_games_together` threshold are omitted from the output (they
   are still in the fit so they don't distort other estimates).

### Tunable knobs (exposed on the endpoint)

* `regularization` (`λ_pair`, default chosen so a pair needs a meaningful number
  of games to register) — higher ⇒ more conservative.
* `min_games_together` — hide pairs with too little shared history.
* `game_format` — restrict to `2v2` / `3v3` / `4v4`.

### Endpoint

`GET /api/player_ratings/synergy/` → `list[PlayerSynergy]`, sorted by synergy
descending. Same game source and caching pattern as the other rating endpoints.

## Interpreting the numbers

* `synergy > 0`: the pair wins more than their combined ratings predict. At an
  otherwise even (50/50) matchup, their win probability is `0.5 + win_prob_delta`.
* `synergy < 0`: anti‑synergy.
* Trust `|z_score| ≳ 2` and a non‑trivial `games_together`; small‑sample pairs
  are already shrunk toward 0, so a near‑zero synergy on few games means
  "not enough evidence," not "proven neutral."
