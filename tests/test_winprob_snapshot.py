"""What the win-probability-over-time model trains on, and which games it serves.

Torch-free: snapshot, features and pregame import without the ML venv. The
replay-level tests use the gitignored ``references/`` fixtures and skip without
them.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from radarvan.api_types import Team
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2

from ml_win_prediction_over_time import pregame
from ml_win_prediction_over_time.features import (
    FEATURE_NAMES,
    FeatureStats,
    feature_names,
    match_to_sequence,
)
from ml_win_prediction_over_time.snapshot import (
    EV_DEATH,
    EV_KILL,
    EV_KILL_STRUCT,
    Drop,
    app_label,
    record_from_replay,
)

import corpus

REFERENCES = Path(__file__).resolve().parents[1] / "references"
THREE_V_THREE = REFERENCES / "example_cncstats_output.json"
THREE_V_TWO = REFERENCES / "cncstats_json.json"


def _replay(path: Path) -> EnhancedReplayV2:
    if not path.exists():
        pytest.skip(f"{path.name} fixture not present")
    return EnhancedReplayV2.model_validate(json.loads(path.read_text()))


def _record(**overrides: object) -> dict:
    base = {
        "match_id": 1,
        "duration_minutes": 2.0,
        "frame_count": 3600,
        "snapshot_interval": 30,
        "label_a_win": 1,
        "team_a_id": 1,
        "team_size": 2,
        "win_method": "deathEvents",
        "team_a_players": ["Syn", "Skip"],
        "team_b_players": ["Neo", "Gorn"],
        "events": [],
        "money": {"0": [1000] * 4, "1": [1000] * 4},
        "earned": {"0": [0, 100, 200, 300], "1": [0, 50, 100, 150]},
    }
    return {**base, **overrides}


def test_the_label_is_the_winner_the_app_shows() -> None:
    assert app_label(_record(), corpus.match(1, day=1, winner=Team.ONE), False) == 1
    rec = _record(team_a_id=2, label_a_win=0)
    assert app_label(rec, corpus.match(1, day=1, winner=Team.ONE), False) == 0


def test_a_replay_that_disagrees_with_the_app_is_dropped() -> None:
    info = corpus.match(1, day=1, winner=Team.TWO)
    assert app_label(_record(), info, False) == Drop.MISMATCH
    assert app_label(_record(), info, True) == Drop.MISMATCH


def test_an_estimated_winner_counts_only_once_an_admin_has_ruled() -> None:
    rec = _record(win_method="estimatedWinner")
    info = corpus.match(1, day=1, winner=Team.ONE)
    assert app_label(rec, info, False) == Drop.ESTIMATED
    assert app_label(rec, info, True) == 1


def test_a_match_the_app_shows_without_a_winner_is_dropped() -> None:
    assert (
        app_label(_record(), corpus.match(1, day=1, winner=Team.NONE), True)
        == Drop.NO_WINNER
    )


def test_uneven_teams_get_no_record_so_no_training_row_and_no_curve() -> None:
    assert record_from_replay(_replay(THREE_V_TWO)) is None


def test_only_real_enemy_kills_are_recorded() -> None:
    replay = _replay(THREE_V_THREE)
    rec = record_from_replay(replay)
    assert rec is not None
    kills = [e for e in rec["events"] if e[1] in (EV_KILL, EV_KILL_STRUCT)]
    assert kills and all(value > 0 for _, _, _, value in kills)
    assert len(kills) < len(replay.stats.kill_events)  # missiles, debris, hulls gone
    assert any(e[1] == EV_KILL_STRUCT for e in kills)
    assert rec["team_size"] == 3
    assert sum(e[1] == EV_DEATH for e in rec["events"]) == 3


def test_events_after_the_cap_are_dropped_not_folded_into_the_last_window() -> None:
    # 2 minutes = 4 windows; a kill at frame 1e6 is far past the end.
    rec = _record(events=[[10_000_000, EV_KILL, 0, 500]])
    seq = match_to_sequence(rec)
    assert seq is not None
    assert seq.x[-1, FEATURE_NAMES.index("a.kills")] == 0


def test_alive_is_the_share_of_the_side_still_playing() -> None:
    seq = match_to_sequence(_record(events=[[100, EV_DEATH, 1, 0]]))
    assert seq is not None
    assert seq.x[-1, FEATURE_NAMES.index("a.alive")] == 1.0
    assert seq.x[-1, FEATURE_NAMES.index("b.alive")] == 0.5


def test_dropping_a_group_removes_its_a_b_and_difference_columns() -> None:
    names = feature_names(frozenset({"income"}))
    assert not any(n.endswith(".income") for n in names)
    assert len(names) == len(FEATURE_NAMES) - 3
    with pytest.raises(ValueError):
        feature_names(frozenset({"nope"}))


def test_feature_stats_select_and_standardise_their_own_columns() -> None:
    seqs = [
        s
        for i in range(4)
        if (
            s := match_to_sequence(
                _record(money={"0": [1000 * (i + 1)] * 4, "1": [500] * 4})
            )
        )
    ]
    stats = FeatureStats.fit(seqs, ["a.money", "prior"])
    out = stats.apply(seqs[0].x)
    assert out.shape == (seqs[0].length, 2)
    assert np.allclose(
        np.concatenate([stats.apply(s.x) for s in seqs])[:, 0].mean(), 0, atol=1e-5
    )


def test_out_of_fold_prior_never_scores_a_game_it_was_fit_on() -> None:
    """Syn always wins; out of fold, a game is scored by a fit without it."""
    recs = [
        _record(
            match_id=i, team_a_players=["Syn"], team_b_players=[f"p{i}"], label_a_win=1
        )
        for i in range(10)
    ]
    in_sample = pregame.fit(recs)
    oof = pregame.oof_logits(recs, folds=5)
    # Each p{i} appears once: in-sample it has absorbed its own loss, out of fold
    # it is unknown and contributes nothing.
    assert all(z < in_sample.logit(["Syn"], [f"p{i}"]) for i, z in enumerate(oof))
