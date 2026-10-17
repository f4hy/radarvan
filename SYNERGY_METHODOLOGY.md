# Player Synergy Methodology

## Goal

For every pair of players, decide whether they win **more or less often as
teammates than the rating model expected**. Implemented in
`radarvan/player_synergy.py`, served by `GET /api/player_ratings/synergy/`.

## Method

1. **Replay the ratings chronologically.** `pregame_expectations` runs the same
   rating update as `player_rating.compute_player_ratings`, from the same initial
   seeds. Before each game it records each team's win probability from
   `displayed_win_probs` (the app's calibrated probability), using the ratings as
   they stood *before* that game. A game's own result never affects its
   expectation, and future games never change earlier ones.
2. **Credit every teammate pair.** Each pair on a team gets that game's
   `outcome − probability` (outcome 1 for a win, 0 for a loss).
3. **Sum per pair.** For each pair we report:

   | Field | Meaning |
   |---|---|
   | `games_together`, `wins_together` | the raw record as teammates |
   | `expected_wins` | sum of the pregame probabilities |
   | `excess_wins` | `wins_together − expected_wins` |
   | `win_rate_delta` | `excess_wins / games_together`, the synergy (shown in percentage points) |
   | `z_score` | `excess_wins / sqrt(Σ p(1−p))`, excess over the model's own standard deviation of wins |
   | `solo_a`, `solo_b` | each player's per-game excess in games *without* the other; `None` under `MIN_SOLO_GAMES` (5) games apart |

Results are sorted by `z_score`. No shrinkage is applied: `z` is what keeps a
3-game +40pp pair from outranking a 150-game +6pp one.

## Reading the solo columns

These are shared team residuals, not isolated chemistry. Every pair on a team
gets the same credit, including effects from other teammates and from opponents.
The biggest confounder is a player the rating model *underrates*, such as an
improving player whose rating lags: they beat expectations in most games, so
every pair containing them looks positive. The solo baselines show this directly.
A pair whose synergy is close to `solo_a + solo_b` is mostly the players, not the
pairing. They are shown rather than subtracted because a baseline from few
games apart is noisy, and subtracting it inflates small pairs.

The ratings also absorb some of a pair's own past results: if A and B mostly
play together, their wins raise both ratings, which raises later expectations.
The measure is therefore conservative for pairs that rarely play apart.

## Which games count

- Rating updates use the normal eligibility rules (`is_ratable_team_game`),
  including CPU games, guest games and tournament 1v1s.
- Pair and solo tallies skip CPU and guest games (a guest's seeded rating is a
  guess). 1v1s have no pairs.
- Format filtering (`game_format`) happens *after* the full replay, so a 2v2 view
  still uses earlier 3v3/4v4 history to set its expectations. The solo baselines
  are restricted to the same format as the pair.
- The `DISPLAY_BETA` calibration constant was fitted over the whole corpus, so
  this is not a fully held-out evaluation of calibration.

## Where it's used

- The Player Synergy page (full table) and the Rating Trend page's public view
  (pairs with ≥10 games together and |z| ≥ 2).
- A player profile's favorite teammate: their highest-`z` pair, falling back to
  the most frequent teammate. `TeammateProfileStat.synergy` carries that pair's
  `win_rate_delta`, which also appears in the matchup commentary prompt.
