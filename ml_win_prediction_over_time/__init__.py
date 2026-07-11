"""Win-probability-over-time model for Zero Hour matches.

Unlike the pre-game outcome model in ``ml/`` (which predicts the winner from the
match's *inputs* — players, generals, map), this model watches the match unfold:
it consumes the full in-game event stream (builds, kills, captures, money) and
emits a calibrated P(team A wins) at every point in time, like an esports win
probability bar.

See ``README.md`` for the pipeline and ``model_design`` notes in the README.
"""
