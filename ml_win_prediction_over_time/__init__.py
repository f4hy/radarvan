"""Win-probability-over-time model for Zero Hour matches.

Unlike the pre-game outcome model in ``ml/`` (which predicts the winner from the
match's *inputs* — players, generals, map), this model watches the match unfold:
it consumes the full in-game event stream (builds, kills, captures, money),
seeded with a frozen pre-game prior over the rosters, and emits P(team A wins)
at every point in time, like an esports win probability bar.

"Calibrated" is meant literally: a temperature is fitted on held-out games and
baked into the exported graph (``export.py``). It used to say so here with no
calibration step anywhere in the module.

See ``README.md`` for the pipeline and ``model_design`` notes in the README.
"""
