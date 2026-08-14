"""Per-map, per-player records - what the bracket Map List tab expands into."""

from datetime import date, datetime

from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.map_stats import map_player_records


def _match(
    match_id: int,
    *,
    map_path: str,
    winner: str,
    p1: str,
    p2: str,
    incomplete: str = "",
    observer: str | None = None,
) -> MatchInfo:
    players = [
        Player(
            name=p1, general=General.USA, team=Team.ONE, color="red", won=p1 == winner
        ),
        Player(
            name=p2, general=General.GLA, team=Team.TWO, color="blue", won=p2 == winner
        ),
    ]
    if observer is not None:
        players.append(
            Player(
                name=observer,
                general=General.UNRECOGNIZED,
                team=Team.OBSERVER,
                color="-1",
                won=False,
            )
        )
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        date=date(2026, 1, 1),
        map=map_path,
        winning_team=Team.ONE if p1 == winner else Team.TWO,
        players=players,
        duration_minutes=10.0,
        filename=f"game_{match_id}.rep",
        incomplete=incomplete,
    )


def test_records_group_by_map_then_player() -> None:
    games = [
        _match(1, map_path="maps/vendetta", winner="Skip", p1="Skip", p2="Neo"),
        _match(2, map_path="maps/vendetta", winner="Neo", p1="Skip", p2="Neo"),
        _match(3, map_path="maps/canyon", winner="Neo", p1="Skip", p2="Neo"),
    ]

    records = map_player_records(games)

    # Maps are ordered by games played, so Vendetta (2) precedes Canyon (1).
    assert [(m.map_key, m.total_games) for m in records] == [
        ("vendetta", 2),
        ("canyon", 1),
    ]
    vendetta, canyon = records
    assert {(p.player, p.wins, p.losses) for p in vendetta.players} == {
        ("Skip", 1, 1),
        ("Neo", 1, 1),
    }
    # Within a map, the player with more wins sorts first on equal games.
    assert [(p.player, p.wins, p.losses) for p in canyon.players] == [
        ("Neo", 1, 0),
        ("Skip", 0, 1),
    ]


def test_map_key_joins_paths_case_and_whitespace() -> None:
    games = [
        _match(
            1,
            map_path="userdata/maps/[rank] vendetta zh v1",
            winner="Skip",
            p1="Skip",
            p2="Neo",
        ),
        _match(
            2,
            map_path="Maps/[RANK] Vendetta ZH v1.map",
            winner="Neo",
            p1="Skip",
            p2="Neo",
        ),
    ]

    (record,) = map_player_records(games)
    assert record.map_key == "[rank]vendettazhv1"
    assert record.total_games == 2
    assert {(p.player, p.wins, p.losses) for p in record.players} == {
        ("Skip", 1, 1),
        ("Neo", 1, 1),
    }


def test_aliases_resolve_and_non_participants_are_skipped() -> None:
    games = [
        # "grn" is Gorn's in-game alias; the observer never played.
        _match(
            1,
            map_path="maps/vendetta",
            winner="grn",
            p1="grn",
            p2="131",
            observer="Skip",
        ),
        # An unfinished game counts for nobody.
        _match(
            2,
            map_path="maps/vendetta",
            winner="131",
            p1="grn",
            p2="131",
            incomplete="disconnect",
        ),
    ]

    (record,) = map_player_records(games)

    # Only the decided game counts, and the observer isn't in it.
    assert record.total_games == 1
    assert [(p.player, p.wins, p.losses) for p in record.players] == [
        ("Gorn", 1, 0),
        ("OneThree111", 0, 1),
    ]
