"""Per-game general matchups for the bracket's Factions & Matchups tab."""

from datetime import date, datetime

from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.bracket_factions import bracket_faction_games
from radarvan.db import TournamentGame


def _match(
    match_id: int,
    winner: str,
    p1: tuple[str, General],
    p2: tuple[str, General],
    *,
    minute: int = 0,
    incomplete: str = "",
) -> MatchInfo:
    players = [
        Player(name=name, general=general, team=team, color=color, won=name == winner)
        for (name, general), team, color in (
            (p1, Team.ONE, "red"),
            (p2, Team.TWO, "blue"),
        )
    ]
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 8, 9, 2, minute),
        date=date(2026, 8, 8),
        map="maps/vendetta",
        winning_team=Team.ONE if p1[0] == winner else Team.TWO,
        players=players,
        duration_minutes=10.0,
        filename=f"game_{match_id}.rep",
        incomplete=incomplete,
    )


def _link(match_id: int, stage: str | None = "LB1-2") -> TournamentGame:
    return TournamentGame(
        tournament_id=1, match_id=match_id, stage=stage, round_name="Losers Round 1"
    )


def test_marks_games_won_by_the_set_loser() -> None:
    known = {
        1: _match(
            1, "Skip", ("Skip", General.AIR), ("Neo", General.STEALTH), minute=20
        ),
        2: _match(2, "Neo", ("Skip", General.TANK), ("Neo", General.LASER), minute=10),
    }
    rows = bracket_faction_games([_link(1), _link(2)], known, {"LB1-2": "Neo"})

    assert [
        (r.match_id, r.winner, r.winner_general, r.loser_general, r.winner_lost_set)
        for r in rows
    ] == [
        (2, "Neo", General.LASER, General.TANK, False),
        (1, "Skip", General.AIR, General.STEALTH, True),
    ]


def test_unscored_set_leaves_the_flag_unknown() -> None:
    known = {1: _match(1, "Skip", ("Skip", General.AIR), ("Neo", General.TOXIN))}
    [row] = bracket_faction_games([_link(1)], known, {"LB1-2": None})
    assert row.winner_lost_set is None


def test_skips_undecided_unknown_and_stageless_games() -> None:
    known = {
        1: _match(
            1,
            "Skip",
            ("Skip", General.AIR),
            ("Neo", General.TOXIN),
            incomplete="disconnect",
        ),
        2: _match(2, "Skip", ("Skip", General.AIR), ("Neo", General.TOXIN)),
        3: _match(3, "Skip", ("Skip", General.AIR), ("Neo", General.TOXIN)),
    }
    links = [_link(1), _link(2, stage=None), _link(3), _link(99)]
    rows = bracket_faction_games(links, known, {"LB1-2": "Skip"})
    assert [r.match_id for r in rows] == [3]
