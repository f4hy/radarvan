"""Recency weighting of training games.

Old games describe players who no longer play that way (the median regular's
win rate moves ~10 points a year), so training down-weights them by age. The
properties that matter: the decay is anchored to the newest game *in the block*
(not to today, or the weights would drift with the wall clock), a game one
half-life older weighs half as much, and the mean weight stays 1.0 so the loss
scale - and with it the learning rate - does not depend on the half-life.
"""

from datetime import date, datetime

import pytest

from ml.features import EncodedMatch, EncodedPlayer, recency_weighted
from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.game_composition import MatchRoster
from radarvan.player_role import PlayerRole


def _encoded(match_id: int, day: date) -> EncodedMatch:
    p = EncodedPlayer(player=1, general=1, faction=1, start_pos=0)
    return EncodedMatch(
        match_id=match_id,
        map=1,
        map_feat=[],
        fmt=1,
        team_a=[p],
        team_b=[p],
        label=1,
        duration_minutes=10.0,
        date_ordinal=day.toordinal(),
    )


def test_none_half_life_leaves_weights_uniform() -> None:
    matches = [_encoded(1, date(2022, 1, 1)), _encoded(2, date(2026, 1, 1))]
    assert [m.weight for m in recency_weighted(matches, None)] == [1.0, 1.0]


def test_newest_match_anchors_the_decay() -> None:
    """Half-life apart => half the weight, whatever the absolute dates are."""
    newest = date(2026, 1, 1)
    older = date(2025, 1, 1)  # 365 days earlier
    weighted = recency_weighted([_encoded(1, older), _encoded(2, newest)], 365)
    old_w, new_w = weighted[0].weight, weighted[1].weight
    assert old_w == pytest.approx(new_w / 2, rel=1e-6)


def test_weights_average_to_one() -> None:
    matches = [_encoded(i, date(2020 + i // 4, 1 + i % 4, 1)) for i in range(24)]
    weighted = recency_weighted(matches, 400)
    mean = sum(m.weight for m in weighted) / len(weighted)
    assert mean == pytest.approx(1.0, rel=1e-9)


def test_input_is_not_mutated() -> None:
    matches = [_encoded(1, date(2022, 1, 1)), _encoded(2, date(2026, 1, 1))]
    recency_weighted(matches, 365)
    assert [m.weight for m in matches] == [1.0, 1.0]


def test_absolute_dates_do_not_matter_only_gaps() -> None:
    """Re-scoring the same block years later must not change its weights."""
    def pair(start: date) -> list[float]:
        later = date.fromordinal(start.toordinal() + 365)
        return [m.weight for m in recency_weighted(
            [_encoded(1, start), _encoded(2, later)], 365
        )]

    assert pair(date(2024, 1, 1)) == pytest.approx(pair(date(2019, 1, 1)))


def test_non_positive_half_life_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        recency_weighted([_encoded(1, date(2026, 1, 1))], 0)


def test_empty_input() -> None:
    assert recency_weighted([], 365) == []


def test_encode_match_carries_the_date() -> None:
    """The ordinal has to survive encoding, or every weight collapses to equal."""
    from ml.features import build_vocab, encode_match

    when = datetime(2026, 3, 4, 12, 0, 0)
    players = [
        Player(name="Skip", general=General.USA, team=Team.ONE, color="red",
               won=True, role=PlayerRole.HUMAN),
        Player(name="Neo", general=General.TANK, team=Team.TWO, color="blue",
               won=False, role=PlayerRole.HUMAN),
    ]
    match = MatchInfo(
        id=7,
        timestamp=when,
        date=when.date(),
        map="some_map",
        winning_team=Team.ONE,
        players=players,
        duration_minutes=12.0,
        filename="game_7.rep",
        composition=MatchRoster.from_players(players).composition(),
    )
    encoded = encode_match(match, build_vocab([match]))
    assert encoded is not None
    assert encoded.date_ordinal == when.date().toordinal()
    assert encoded.weight == 1.0
