# Equal-skill composition and map predictor

Status: Phase 1 implemented — `ml/scenario.py` (model), `ml/scenario_train.py`
(fit/eval/export to `ml_scenario/scenario_model.json`), `radarvan/scenario_inference.py`
and `/api/scenario/*`, page `/composition-predictor`. Phases 2–3 are not built.
Findings at implementation (snapshot-20261024): generals are always assigned at
random in this group (players never choose), so the selection concerns below
don't apply and player adjustment only reduces noise; penalties were tuned by game-night CV rather than chronological cuts,
because the early cuts overfit the interaction blocks. Every block moves held-out
log-loss by under 0.002. The supported effects are Stealth (strong), China (weak)
and mixed-faction teammates (USA+GLA, USA+China); general-level synergy and
map interactions shrink close to zero.

## Product goal

Answer questions such as:

> Given Laser + GLA versus China + Toxin on this map, which composition is
> favored between equally skilled players? Does the outlook change if the
> game reaches the late game?

This is separate from predicting the winner of an actual lobby. The existing
player-sensitive predictor can continue answering that question. This model's
public inputs are generals, team composition, map, and eventually time—not
player identities.

General, composition, and map sensitivity are requirements. Aggregate win
prediction accuracy alone does not determine success. However, we should not
manufacture visible differences where evidence supports only a small effect.

## What the prediction means

The initial output is a **model-based equal-skill matchup estimate**:

- Both sides have the same reference player skill and general familiarity.
- The estimate reflects the strategies and game settings represented in the
  training population, rather than optimal theoretical play.
- Map and composition effects remain active.
- Player identities do not enter the serving request.

Fit player effects during training, then set them to their centered reference
values at scenario inference. Removing player identities from training would
instead allow strong players' preferred generals to inherit their strength.

This adjustment does not establish a causal game-balance effect. Unrecorded
strategy, coordination, selection of generals, and settings can still confound
the result. Some scenarios cannot be separated from player effects with the
available observations; shrinkage provides an assumption-based estimate, not
new evidence.

The reference is a common skill level, not an average of arbitrary real-player
predictions. Averaging over skill distributions is a different estimand because
the probability link is nonlinear. If skill-dependent composition effects are
introduced later, expose explicit skill tiers rather than silently changing the
meaning of the default prediction.

## Available evidence

Counts from the local `snapshot-20261024.jsonl.gz`, inspected on 2026-10-24:

| Property | Count |
|---|---:|
| Usable two-team matches | 1,387 |
| Player identities, including AI identities | 20 |
| 1v1 / 2v2 / 3v3 / 4v4 | 63 / 583 / 537 / 204 |
| Distinct maps | 194 |
| Maps with fewer than five games | 121 |
| Observed player–general combinations | 223 |
| Player–general combinations with fewer than ten appearances | 78 |
| Distinct dates | 320 |
| Games in repeated team-versus-team fixtures | 1,200 |

One game supplies one outcome, regardless of how many player or general pairs
it contains. Pair appearances must not be treated as independent matches.

These counts favor a small structured model with shared effects. Independent
curves for every composition on every map are not feasible. Repeated fixtures
may be valuable when their generals or maps change, but repetition without
such changes does little to identify matchup effects.

## Phase 0: audit identifiability and inputs

Produce a support report before fitting new interactions:

1. Player-by-general counts, by time period and format; identify players who
   switch generals and combinations confined to one player.
2. Repeated rosters with changed generals or maps; count both exact and partial
   comparisons and report whether opponents also changed.
3. General selection mechanism: distinguish random assignment from deliberate
   selection if it was recorded. Do not infer random assignment merely from
   the final general. Random selection can strengthen evidence but does not
   randomize rosters or maps.
4. Coverage and correctness of map geometry, versions, game settings, AI slots,
   results, duration, disconnects, and incomplete recordings.
5. Whether enough replay data exists to reconstruct measurements at fixed
   elapsed times. The current outcome encoding has final duration; that does
   not establish availability of reliable trajectories.

Keep the initial scope to supported two-team, equal-size formats. Treat CPU
games as a separate domain or explicitly model AI effects; do not silently
equate AI identities with human skill. Compare including and excluding them.
Record eligibility rules in each snapshot manifest.

## Phase 1: structured equal-skill outcome model

Use a regularized logistic model with explicit additive components. A practical
first implementation is a maximum-a-posteriori fit with Gaussian penalties;
full Bayesian inference is optional, not a prerequisite.

For teams A and B on map m:

```text
logit P(A wins) =
    player_adjustment(A, B, date)
  + familiarity_adjustment(A, B)
  + general_strength(A) - general_strength(B)
  + composition_synergy(A) - composition_synergy(B)
  + general_counters(A, B)
  + map_interactions(A, B, geometry(m))
```

At scenario inference, the two player-related adjustments are zero. Optional
player-pair coordination adjustments used during fitting must also be zero.
Keep these nuisance adjustments strongly regularized and test their influence
on the composition estimates.

### Player adjustment

Start with one centered strength per player and a modest time-drift model, or
a recency-weighted static fit as the simpler comparison. Use shared drift
regularization rather than a separate freely tuned trajectory for each player.
Historical evaluation must fit only information available before each cut.

Player–general familiarity is a centered deviation from player and general
main effects, with strong shrinkage toward zero. This is important when some
players specialize in a general. Separating familiarity from general strength
will remain uncertain where players rarely switch.

### General strength and composition

- General main effects: twelve centered coefficients, with optional faction
  family means and shrunk general deviations.
- Composition synergy: symmetric general-pair effects within a team. This is
  **general-pair synergy**, not the current model's player-pair synergy.
- Counters: skew-symmetric opposing-general effects, so reversing the teams
  reverses their contribution.

Average individual contributions, normalize teammate effects by the number of
pairs, and normalize counters by the number of cross-team pairs. Synergy is
zero for a one-player team. Treat these normalizations as initial inductive
biases; evaluate a small, shrunk format-scale extension if calibration differs
systematically by format.

Use separate regularization strengths for main effects, familiarity, synergy,
counters, and map interactions. Sparse interactions should shrink much more
strongly than well-supported main effects. Prefer faction-level sharing before
adding unrestricted general-level interactions.

### Identifiability constraints

An additive general-strength difference can also be represented by a counter
matrix `C[g,h] = b[g] - b[h]`. Without constraints, the displayed strength and
counter components can exchange the same effect.

Center main effects; constrain the counter matrix to be skew-symmetric with
zero row sums under a fixed reference weighting. Center familiarity deviations
across their player and general margins. Remove main-effect directions from
the synergy design as well. Document the reference weighting and verify the
design rank numerically, including duplicate-general compositions.

These constraints define the decomposition; they do not solve a lack of
observational overlap. Overall prediction stability and component stability
must both be measured.

### Map effects

A shared map intercept cannot favor one side. Maps should change relative
strength through interactions with team composition.

Start with general-by-geometry interactions, centered so they do not duplicate
general main effects. The existing `map_features.py` supplies:

- Log map area.
- Log supply-object count per starting position.
- Log tech-object count per starting position.

Audit the meaning of these proxies: object counts are not necessarily resource
amounts, and tech-object counts are not automatically oil income. Candidate
extensions include rush distance, resource accessibility, and openness, only
after reliable extraction is demonstrated.

Do not start with a free effect for every composition/map combination. Add
heavily shrunk map-identity interaction residuals only if geometry leaves
repeatable unexplained effects. Unseen maps with valid geometry can share
evidence; missing geometry should produce an explicit fallback marker.

Spawn positions are a later feature. If used, associate them with the actual
teams and preserve team-swap symmetry. A map-only request should either
average over a stated spawn distribution or explicitly specify the layout.

### Structural requirements

- Permuting players/generals within a team leaves predictions unchanged.
- Swapping teams gives complementary probabilities.
- Identical compositions under symmetric map/spawn assumptions give 50%.
- Missing or unsupported inputs have documented fallbacks.
- Explanations report contributions on the logit scale; probability changes
  are calculated by rerunning the scenario, not by adding percentage points.

## Phase 2: win timing and outlook conditional on survival

Winner and final duration can support a discrete-time competing-risks model.
They cannot by themselves identify intrinsic army strength at each minute.

For each interval k, conditional on the game still running, predict:

```text
h_A(k) = P(A wins during interval k | game active at its start, scenario)
h_B(k) = P(B wins during interval k | game active at its start, scenario)
h_continue(k) = 1 - h_A(k) - h_B(k)
```

Use a three-outcome softmax so probabilities are valid. Separate a symmetric
game-ending pace component from an antisymmetric side-advantage component;
swapping teams must exchange the A/B hazards and preserve continuation.
Allow geometry to affect pace even where it does not favor a side.

Represent time with a few smooth basis functions. Begin with time-varying
general effects; add time-varying synergy or map interactions only after
evidence supports them. Reuse the player adjustments from Phase 1 and
neutralize them at scenario inference.

From the hazards compute survival and cumulative win incidence:

```text
S(0) = 1
S(k+1) = S(k) * h_continue(k)
F_A(K) = sum over k < K of S(k) * h_A(k)
F_B(K) = sum over k < K of S(k) * h_B(k)
```

Expose clearly distinguished outputs:

- Probability A or B has won by a given minute.
- Probability the game is still running.
- Conditional outlook if the game has reached a given minute, with no further
  information about its state.

Conditional outlook to a finite horizon must retain unresolved probability.
Do not silently normalize unresolved games away or claim eventual victory
probabilities without a justified tail treatment. Shade or truncate time
ranges with little surviving support.

Example wording, only when the fitted estimates support it:

> China + Toxin is more likely to finish the game early. Among games that
> reach the later period, the modeled outlook shifts toward Laser + GLA.

Do not translate this into “waiting makes Laser stronger” or “stalling causes
a higher win chance.” Survival selects games and strategies. A final-duration
feature in an ordinary outcome classifier would obscure this distinction.

Use the match-level survival likelihood. Expanded time intervals are not
independent games for splitting, bootstrapping, or counting evidence. Audit
disconnects and incomplete observations before treating them as ordinary
finishes or non-informative censoring.

## Phase 3: replay trajectory model, if data permits

To describe how economic or military advantage develops, reconstruct reliable
measurements at fixed timestamps: resources, income, army value, production,
losses, or map control where actually available.

Keep two questions separate:

1. **Pre-game scenario forecast:** expected distributions of trajectories for
   an equal-skill matchup; cannot consume the future state of the target game.
2. **Live state forecast:** winning outlook given an observed game state;
   receives those measurements and answers a different question.

Alive-at-minute summaries are survivor-selected. Show survival alongside
trajectory summaries and define how finished games are handled. Different
factions' army values may not be directly comparable, so avoid claiming one
proxy is universal “power.”

This phase requires a separate data audit and target definition; it should not
block the initial composition predictor.

## Evaluation: accuracy and scenario usefulness

### Historical prediction

- Use chronological outer evaluation blocks, with session/date boundaries
  where appropriate. Tune penalties and architecture on inner temporal splits.
- Keep tournament 1v1s chronological; do not move future games into training
  to populate a format vocabulary.
- Save predictions by match ID and compare exactly the same eligible games.
- Report log-loss, Brier score, calibration, and per-format performance.
- Evaluate the full player-adjusted model against real outcomes. Do not score
  its equal-skill projection against unequal-skill games as if those were the
  corresponding counterfactual labels.
- Use paired session/date-block resampling for uncertainty; report sensitivity
  to the block definition rather than assuming all games are independent.

The existing player-only baseline remains a useful accuracy reference, but it
cannot satisfy the scenario requirement and therefore is not a complete
product substitute.

### Scenario evaluation

Maintain a versioned suite of representative lobbies, maps, and single-input
changes. For every candidate, measure:

- Direction and magnitude of general/map/composition changes.
- Stability across bootstrap fits, training periods, and regularization choices.
- Dependence on player adjustment: do apparent general effects disappear when
  player strength and familiarity are accounted for?
- Performance on held-out repeated-fixture comparisons where compositions or
  maps changed, while acknowledging remaining selection bias.
- Transfer to unseen map names with known geometry.
- Symmetry and permutation invariants.

Add synthetic recovery experiments with known skill and composition effects,
including confounded selection patterns. These test whether the implementation
can recover identifiable effects and expresses uncertainty when it cannot;
they do not validate real-game assumptions.

Do not reward larger scenario differences as an objective. Reward supported,
stable differences and honest uncertainty. A model that invents a crossover
for every matchup is failing the product goal.

For the temporal extension, evaluate survival likelihood, win incidence by
horizon, and conditional calibration among games still active. Report the
number of games at risk in late intervals.

## Serving and presentation

Keep this predictor's artifacts and API separate from actual-lobby prediction.
A request contains team general lists, map identity or validated geometry,
format, and optional supported spawn configuration. No player IDs are needed.

Return:

- Equal-skill win probability and a clearly labeled model uncertainty interval.
- Reference-population and model-version metadata.
- Support information: exact matches, broader composition/general evidence,
  map-feature coverage, and extrapolation flags.
- Scenario differences relative to a requested comparison, with uncertainty
  estimated from paired predictions within each fitted replicate.
- When available, time curves with surviving support and unresolved tail mass.

Bootstrap spread measures sensitivity to the fitting data and procedure, not
all uncertainty from confounding or misspecification. Label it accordingly.
Support should not be reduced to a single arbitrary confidence score.

Use an “equal skill and familiarity” label near the prediction. For weak
comparisons say the evidence does not distinguish the choices. Do not require
every change of map or general to move the displayed rounded percentage.

## Implementation sequence and decision gates

1. Build the support/overlap and replay-input audit from frozen snapshots.
2. Fit player-adjusted general main effects; verify synthetic recovery and
   invariants before expanding the design.
3. Add shrunk general-pair synergy, residual counters, and general-by-geometry
   interactions one block at a time.
4. Compare the structured model with the current neural model on both
   historical predictions and the fixed scenario suite. Check sensitivity to
   nuisance-player specifications before interpreting general effects.
5. Select a configuration with acceptable forecast calibration and stable
   scenario effects; package its equal-skill projection as a separate artifact.
6. Audit durations and implement the competing-risks extension. Publish time
   curves only over supported intervals, without requiring a crossover.
7. Pursue trajectory modeling only after confirming replay coverage and
   defining what “advantage” means operationally.

Predefine acceptable calibration degradation and useful scenario precision
before selecting a winner. If the data cannot distinguish an effect, retain a
shrunk estimate with uncertainty or defer that feature; do not solve lack of
support by increasing network capacity.

The central design choice is to **learn from actual players while answering
at a common player reference**. This preserves the desired composition and map
behavior without deliberately attributing player ability to game balance.
