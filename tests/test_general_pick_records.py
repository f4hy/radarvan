"""Per-general pick records - what the bracket Factions tab shows."""

from datetime import date, datetime

from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.general_stats import general_pick_records


def _match(
    match_id: int,
    *,
    winner: str,
    p1: tuple[str, General],
    p2: tuple[str, General],
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
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        date=date(2026, 1, 1),
        map="maps/vendetta",
        winning_team=Team.ONE if p1[0] == winner else Team.TWO,
        players=players,
        duration_minutes=10.0,
        filename=f"game_{match_id}.rep",
        incomplete=incomplete,
    )


def test_records_group_by_general_then_player() -> None:
    games = [
        _match(1, winner="Skip", p1=("Skip", General.AIR), p2=("Neo", General.TOXIN)),
        _match(2, winner="Neo", p1=("Skip", General.AIR), p2=("Neo", General.AIR)),
        _match(3, winner="Neo", p1=("Skip", General.NUKE), p2=("Neo", General.TOXIN)),
        _match(
            4,
            winner="Skip",
            p1=("Skip", General.NUKE),
            p2=("Neo", General.TOXIN),
            incomplete="disconnect",
        ),
    ]

    records = general_pick_records(games)

    # Most-picked first; the disconnected game counts for nobody.
    assert [r.general for r in records] == [General.AIR, General.TOXIN, General.NUKE]
    assert [(p.player, p.wins, p.losses) for p in records[0].players] == [
        ("Skip", 1, 1),
        ("Neo", 1, 0),
    ]
