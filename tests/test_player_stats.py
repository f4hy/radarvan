"""Player win/loss stats: total_games helper and get_player_stats aggregation."""

from datetime import date, datetime

from radarvan.api_types import (
    General,
    MatchInfo,
    Player,
    PlayerStat,
    Team,
    WinLoss,
)
from radarvan.game_composition import GameComposition
from radarvan.player_stats import get_player_stats, total_games


def _comp(category: str = "1v1", **overrides: object) -> GameComposition:
    """A competitive composition by default; override fields to break that."""
    base: dict[str, object] = {
        "category": category,
        "is_comp_stomp": False,
        "is_ffa": False,
        "num_teams": 2,
        "team_sizes": [1, 1],
        "total_players": 2,
        "num_humans": 2,
        "num_computers": 0,
        "is_balanced": True,
        "is_1v1": True,
        "is_team_game": True,
    }
    base.update(overrides)
    return GameComposition(**base)  # type: ignore[arg-type]


def _match(
    match_id: int,
    *,
    winner: str,
    p1: tuple[str, General],
    p2: tuple[str, General],
    comp: GameComposition | None = None,
    category: str = "1v1",
    incomplete: str = "",
    filename: str | None = None,
) -> MatchInfo:
    if comp is None:
        comp = _comp(category)
    if filename is None:
        filename = f"game_{match_id}_{category}_map.rep"
    players = [
        Player(
            name=p1[0],
            general=p1[1],
            team=Team.ONE,
            color="red",
            won=(p1[0] == winner),
        ),
        Player(
            name=p2[0],
            general=p2[1],
            team=Team.TWO,
            color="blue",
            won=(p2[0] == winner),
        ),
    ]
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        date=date(2026, 1, 1),
        map="some_map",
        winning_team=Team.ONE if p1[0] == winner else Team.TWO,
        players=players,
        duration_minutes=10.0,
        filename=filename,
        incomplete=incomplete,
        composition=comp,
    )


def test_total_games_sums_all_categories() -> None:
    stat = PlayerStat(
        player_name="Alice",
        stats={
            General.USA: WinLoss(wins=3, losses=2),
            General.CHINA: WinLoss(wins=1, losses=4),
        },
        faction_stats=[],
        over_time=[],
    )
    assert total_games(stat) == 10


def test_total_games_zero_when_empty() -> None:
    stat = PlayerStat(player_name="Bob", stats={}, faction_stats=[], over_time=[])
    assert total_games(stat) == 0


def _alice_wins(n_win: int, n_loss: int) -> list[MatchInfo]:
    games = []
    mid = 1
    for _ in range(n_win):
        games.append(
            _match(
                mid, winner="Alice", p1=("Alice", General.USA), p2=("Bob", General.GLA)
            )
        )
        mid += 1
    for _ in range(n_loss):
        games.append(
            _match(
                mid, winner="Bob", p1=("Alice", General.USA), p2=("Bob", General.GLA)
            )
        )
        mid += 1
    return games


def test_win_loss_counts_for_competitive_games() -> None:
    games = _alice_wins(6, 4)  # 10 games, above NEEDED_GAMES threshold (8)
    result = get_player_stats(games)

    by_name = {s.player_name: s for s in result.player_stats}
    assert "Alice" in by_name
    alice = by_name["Alice"]
    assert alice.stats[General.USA] == WinLoss(wins=6, losses=4)
    assert total_games(alice) == 10

    # Bob mirrors Alice: 4 wins, 6 losses on GLA.
    bob = by_name["Bob"]
    assert bob.stats[General.GLA] == WinLoss(wins=4, losses=6)


def test_players_below_threshold_are_excluded() -> None:
    games = _alice_wins(2, 1)  # only 3 games, <= NEEDED_GAMES
    result = get_player_stats(games)
    assert result.player_stats == []


def test_non_competitive_games_excluded_from_win_loss() -> None:
    # Enough competitive 1v1 games to keep Alice in the output...
    games = _alice_wins(5, 4)  # 9 games
    # ...plus a comp-stomp game Alice "wins" that must NOT add to her W/L.
    stomp = _match(
        999,
        winner="Alice",
        p1=("Alice", General.USA),
        p2=("Bob", General.GLA),
        comp=_comp(is_comp_stomp=True),
    )
    result = get_player_stats([*games, stomp])

    alice = {s.player_name: s for s in result.player_stats}["Alice"]
    # Still 5 wins (the comp-stomp win is not counted), 4 losses.
    assert alice.stats[General.USA] == WinLoss(wins=5, losses=4)
    # game_counts include ALL games that pass the path/incomplete filters,
    # so the non-competitive game is reflected there.
    assert alice.game_counts["total"] == 10
    assert alice.game_counts["1v1"] == 10


def test_format_filter_restricts_win_loss() -> None:
    # 10 competitive 1v1 games (Alice 7-3 on USA)...
    games: list[MatchInfo] = []
    mid = 1
    for _ in range(7):
        games.append(
            _match(
                mid, winner="Alice", p1=("Alice", General.USA), p2=("Bob", General.GLA)
            )
        )
        mid += 1
    for _ in range(3):
        games.append(
            _match(
                mid, winner="Bob", p1=("Alice", General.USA), p2=("Bob", General.GLA)
            )
        )
        mid += 1
    # ...plus 4 competitive 2v2 games Alice wins on CHINA, with a 2v2 filename.
    comp_2v2 = _comp(category="2v2", is_1v1=False)
    for _ in range(4):
        games.append(
            _match(
                mid,
                winner="Alice",
                p1=("Alice", General.CHINA),
                p2=("Bob", General.GLA),
                comp=comp_2v2,
                category="2v2",
            )
        )
        mid += 1

    only_1v1 = get_player_stats(games, game_format="1v1")
    alice = {s.player_name: s for s in only_1v1.player_stats}["Alice"]
    # The 2v2 wins (CHINA) must be excluded by the format filter.
    assert alice.stats[General.USA] == WinLoss(wins=7, losses=3)
    assert alice.stats[General.CHINA] == WinLoss(wins=0, losses=0)
    assert total_games(alice) == 10

    # Without a format filter, both formats count toward W/L.
    all_formats = get_player_stats(games)
    alice_all = {s.player_name: s for s in all_formats.player_stats}["Alice"]
    assert alice_all.stats[General.USA] == WinLoss(wins=7, losses=3)
    assert alice_all.stats[General.CHINA] == WinLoss(wins=4, losses=0)
    assert total_games(alice_all) == 14


def test_incomplete_and_non_team_games_are_skipped() -> None:
    games = _alice_wins(5, 4)  # 9 valid games
    # An incomplete game that would otherwise be a win.
    games.append(
        _match(
            500,
            winner="Alice",
            p1=("Alice", General.USA),
            p2=("Bob", General.GLA),
            incomplete="crash",
        )
    )
    # An FFA composition (not a team game) shouldn't count toward totals either.
    games.append(
        _match(
            501,
            winner="Alice",
            p1=("Alice", General.USA),
            p2=("Bob", General.GLA),
            comp=_comp(category="FFA", is_ffa=True, is_team_game=False),
        )
    )
    result = get_player_stats(games)
    alice = {s.player_name: s for s in result.player_stats}["Alice"]
    # Only the 9 valid games are counted.
    assert alice.stats[General.USA] == WinLoss(wins=5, losses=4)
    assert alice.game_counts["total"] == 9


def test_player_name_aliases_are_resolved() -> None:
    # "skp" resolves to "Skip" via player_ids.resolve_player_name.
    games = []
    mid = 1
    for _ in range(6):
        games.append(
            _match(mid, winner="skp", p1=("skp", General.USA), p2=("Bob", General.GLA))
        )
        mid += 1
    for _ in range(4):
        games.append(
            _match(mid, winner="Bob", p1=("skp", General.USA), p2=("Bob", General.GLA))
        )
        mid += 1
    result = get_player_stats(games)
    names = {s.player_name for s in result.player_stats}
    assert "Skip" in names
    assert "skp" not in names
