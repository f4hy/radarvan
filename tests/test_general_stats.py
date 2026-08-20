"""`general_stats` - per-general win/loss records and the value-destroyed join.

Three functions with no direct coverage before this. The one that most needed it
is the pair `general_value_stats` / `value_stats_from_computed`: they are an
encoder and a decoder for the `__general_value_*` rows the nightly recompute
persists, written in different modules, and nothing checked that they agree.
"""

from datetime import date

from radarvan import general_stats
from radarvan.api_types import (
    General,
    Statistic,
    SuperlativeData,
    SuperlativePlayerSummary,
    Team,
)

from corpus import COLORS, composition, cpu, match, observer  # noqa: F401

TEAM_ONE_GENERALS = (General.USA, General.CHINA)
TEAM_TWO_GENERALS = (General.GLA, General.USA)


def _match_with_generals(match_id: int, *, day: int, winner: Team = Team.ONE, **kw):
    """A 2v2 whose four slots pilot TEAM_ONE_GENERALS then TEAM_TWO_GENERALS."""
    m = match(match_id, day=day, winner=winner, **kw)
    generals = (*TEAM_ONE_GENERALS, *TEAM_TWO_GENERALS)
    return m.model_copy(
        update={
            "players": [
                p.model_copy(update={"general": generals[i]})
                if i < len(generals)
                else p
                for i, p in enumerate(m.players)
            ]
        }
    )


def _records(games) -> dict[General, tuple[int, int]]:
    stats = general_stats.get_generals_stats(games)
    return {s.general: (s.total.wins, s.total.losses) for s in stats.general_stats}


def _superlative(match_id: int, summaries: list[SuperlativePlayerSummary]):
    """The minimum SuperlativeData `general_value_stats` reads: id + summaries."""
    return SuperlativeData(
        match_id=match_id,
        apms=[],
        player_summary=summaries,
        upgrade_counts={},
        total_units_killed=0,
        total_buildings_killed=0,
        total_xp=0,
        match_money_spent=0,
        player_money_collected={},
    )


def _summary(name: str, color: str, *, destroyed: int, lost: int):
    return SuperlativePlayerSummary(
        name=name,
        color=color,
        won=False,
        money_spent=0,
        units_created_count=0,
        buildings_built_count=0,
        value_destroyed=destroyed,
        value_lost=lost,
    )


# --- get_generals_stats -----------------------------------------------------


def test_each_general_gets_the_record_of_the_players_who_picked_it() -> None:
    games = [_match_with_generals(9000 + i, day=5 + i) for i in range(4)]
    records = _records(games)
    # Team one won all four; both of its generals are 4-0, both of team two's 0-4.
    assert records[General.USA] == (4, 4), (
        "USA was piloted on both sides here, so it should carry both results"
    )
    assert records[General.CHINA] == (4, 0)
    assert records[General.GLA] == (0, 4)


def test_incomplete_and_winnerless_games_are_skipped() -> None:
    games = [_match_with_generals(9000 + i, day=5 + i) for i in range(3)]
    baseline = _records(games)
    games.append(_match_with_generals(9100, day=20, incomplete="Disconnect"))
    games.append(_match_with_generals(9101, day=21, winner=Team.NONE))
    assert _records(games) == baseline


def test_a_game_with_more_than_one_cpu_is_skipped() -> None:
    games = [_match_with_generals(9000 + i, day=5 + i) for i in range(3)]
    baseline = _records(games)
    games.append(
        _match_with_generals(
            9102,
            day=22,
            extra_players=(
                cpu(name="TacticalAI", team=Team.THREE),
                cpu(name="EasyArmy", team=Team.THREE, color="pink"),
            ),
        )
    )
    assert _records(games) == baseline, "a two-CPU game reached the leaderboard"


def test_one_cpu_is_allowed_but_the_ai_itself_is_not_scored() -> None:
    games = [
        _match_with_generals(
            9200 + i,
            day=5 + i,
            extra_players=(cpu(name="TacticalAI", team=Team.THREE),),
        )
        for i in range(3)
    ]
    records = _records(games)
    assert records[General.CHINA] == (3, 0), "the human record changed"
    # The CPU pilots USA in the fixture; it must not add to USA's record.
    assert records[General.USA] == (3, 3)


def test_a_general_the_parser_did_not_recognize_is_dropped() -> None:
    """An UNRECOGNIZED slot makes an entry but scores nothing, so it filters out."""
    games = [
        _match_with_generals(9300 + i, day=5 + i).model_copy(
            update={
                "players": [
                    p.model_copy(update={"general": General.UNRECOGNIZED})
                    for p in _match_with_generals(9300 + i, day=5 + i).players
                ]
            }
        )
        for i in range(3)
    ]
    assert _records(games) == {}


def test_results_are_sorted_by_general() -> None:
    games = [_match_with_generals(9000 + i, day=5 + i) for i in range(3)]
    stats = general_stats.get_generals_stats(games)
    order = [s.general for s in stats.general_stats]
    assert order == sorted(order)


def test_an_observer_changes_nothing() -> None:
    plain = [_match_with_generals(9000 + i, day=5 + i) for i in range(4)]
    watched = [
        _match_with_generals(
            9000 + i, day=5 + i, extra_players=(observer(general=General.CHINA),)
        )
        for i in range(4)
    ]
    assert _records(watched) == _records(plain)


# --- the value-destroyed join ----------------------------------------------


def test_value_totals_are_joined_to_the_general_each_player_piloted() -> None:
    game = _match_with_generals(9400, day=5)
    names = [(p.name, p.color) for p in game.players]
    details = [
        _superlative(
            9400,
            [
                _summary(names[0][0], names[0][1], destroyed=100, lost=10),
                _summary(names[1][0], names[1][1], destroyed=200, lost=20),
                _summary(names[2][0], names[2][1], destroyed=300, lost=30),
                _summary(names[3][0], names[3][1], destroyed=400, lost=40),
            ],
        )
    ]
    totals = general_stats.general_value_stats([game], details)
    assert totals[General.CHINA] == (200, 20)
    assert totals[General.GLA] == (300, 30)
    # Slots 0 and 3 both pilot USA, so their totals sum.
    assert totals[General.USA] == (100 + 400, 10 + 40)


def test_details_for_an_unknown_match_are_ignored() -> None:
    game = _match_with_generals(9400, day=5)
    stray = _superlative(999999, [_summary("Skip", COLORS[0], destroyed=999, lost=999)])
    assert general_stats.general_value_stats([game], [stray]) == {}


def test_an_ai_slot_contributes_no_value() -> None:
    """`general_by_match` is built from roster().humans, so an AI simply is not
    in it - this pins that, since the module relies on it instead of a CPU check."""
    game = _match_with_generals(
        9401, day=6, extra_players=(cpu(name="TacticalAI", team=Team.THREE),)
    )
    details = [
        _superlative(
            9401, [_summary("TacticalAI", "yellow", destroyed=5000, lost=5000)]
        )
    ]
    assert general_stats.general_value_stats([game], details) == {}


def test_persisted_rows_decode_back_to_what_was_encoded() -> None:
    """The encoder lives in routes/superlatives, the decoder in general_stats.

    They are the same data crossing a table, so a round trip has to be identity.
    """
    original = {General.USA: (100, 10), General.CHINA: (250, 25)}
    computed = date(2026, 1, 28)
    rows = [
        Statistic(
            stat_name=f"{general_stats.GENERAL_VALUE_STAT_PREFIX}{kind}",
            date_computed=computed,
            value=float(total),
            player=str(int(general)),
        )
        for general, (destroyed, lost) in original.items()
        for kind, total in (("destroyed", destroyed), ("lost", lost))
    ]
    assert general_stats.value_stats_from_computed(rows) == original


def test_rows_that_are_not_value_stats_are_ignored() -> None:
    """The prefix is what separates machine data from the public leaderboard."""
    rows = [
        Statistic(
            stat_name="most_kills",
            date_computed=date(2026, 1, 28),
            value=42.0,
            player="Skip",
        )
    ]
    assert general_stats.value_stats_from_computed(rows) == {}


def test_value_stats_are_attached_to_the_matching_general() -> None:
    games = [_match_with_generals(9000 + i, day=5 + i) for i in range(3)]
    stats = general_stats.get_generals_stats(
        games, value_stats={General.CHINA: (777, 77)}
    )
    by_general = {s.general: s for s in stats.general_stats}
    assert (by_general[General.CHINA].value_destroyed, by_general[General.CHINA].value_lost) == (777, 77)
    assert by_general[General.GLA].value_destroyed == 0, (
        "a general with no value row should read zero, not inherit another's"
    )


def test_a_non_competitive_game_is_skipped() -> None:
    """`competitive_game_filter` gates the leaderboard; a comp-stomp is out."""
    games = [_match_with_generals(9000 + i, day=5 + i) for i in range(3)]
    baseline = _records(games)
    games.append(
        _match_with_generals(
            9103, day=23, comp=composition(is_comp_stomp=True)
        )
    )
    assert _records(games) == baseline
