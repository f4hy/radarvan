"""The pregame text from POST /api/map_summary/, as players see it in the lobby."""

from radarvan.api_types import General
from radarvan.api_types.maps import (
    MapSummaryPlayer,
    MapSummaryPlayerForm,
    MapSummaryPlayerGeneralRecord,
    MapSummaryResponse,
    MapSummaryTeamH2H,
)
from radarvan.api_types.predictions import MatchPrediction
from radarvan.map_stats import format_map_summary

# Listed with team 2 first, to check grouping goes by team id, not request order.
PLAYERS = [
    MapSummaryPlayer(name="Kronos", general=General.STEALTH, team=2),
    MapSummaryPlayer(name="Pancake", general=General.AIR, team=1),
    MapSummaryPlayer(name="Toaster", general=General.SUPER, team=2),
    MapSummaryPlayer(name="Zed", general=General.NUKE, team=1),
]


def _prediction(favored_team: int) -> MatchPrediction:
    return MatchPrediction(
        map_name="Desert",
        team_a=1,
        team_b=2,
        team_a_players=["Pancake", "Zed"],
        team_b_players=["Kronos", "Toaster"],
        prob_team_a_wins=0.38,
        favored_team=favored_team,
        favored_win_prob=0.62,
    )


def _summary() -> MapSummaryResponse:
    records = [(1, 2), (0, 0), (2, 1), (0, 0)]
    forms = [("WWL", "LW"), ("", "WLW"), ("", ""), ("L", "")]
    return MapSummaryResponse(
        map_name="Desert",
        total_games=5,
        team_h2h=MapSummaryTeamH2H(
            team1=["Pancake", "Zed"],
            team2=["Kronos", "Toaster"],
            team1_wins=3,
            team2_wins=2,
        ),
        player_general_records=[
            MapSummaryPlayerGeneralRecord(
                name=p.name, general=p.general, wins=w, losses=lo
            )
            for p, (w, lo) in zip(PLAYERS, records, strict=True)
        ],
        recent_form=[
            MapSummaryPlayerForm(name=p.name, map_form=m, general_form=g)
            for p, (m, g) in zip(PLAYERS, forms, strict=True)
        ],
    )


def test_groups_players_by_team_two_per_line() -> None:
    text = format_map_summary(
        _summary(), PLAYERS, _prediction(favored_team=2), rating_prob_team_a=0.45
    )
    assert text.splitlines() == [
        "Desert: 5 games played here",
        "Balance favors Team B (55%) | AI w/ generals+map: Team B (62%) | "
        "These teams here: A 3-2 B",
        "A: Pancake AIR -/WLW | Zed NUKE L/-",
        "B: Kronos STEALTH 1-2 WWL/LW | Toaster SUPER 2-1",
        "(record here with this general; last 5 here / "
        "last 5 with this general, newest last)",
    ]


def test_new_map_still_says_who_is_on_each_team() -> None:
    """No history means no records, but "Team A" must still mean someone."""
    empty = MapSummaryResponse(map_name="Desert", total_games=0)
    text = format_map_summary(empty, PLAYERS, _prediction(favored_team=1))
    assert text.splitlines() == [
        "Desert: 0 games played here",
        "AI w/ generals+map: Team A (62%)",
        "A: Pancake AIR | Zed NUKE",
        "B: Kronos STEALTH | Toaster SUPER",
    ]


def test_players_without_a_team_get_no_label() -> None:
    players = [
        MapSummaryPlayer(name="Pancake", general=General.AIR),
        MapSummaryPlayer(name="Zed", general=General.NUKE),
    ]
    empty = MapSummaryResponse(map_name="Desert", total_games=0)
    assert format_map_summary(empty, players).splitlines() == [
        "Desert: 0 games played here",
        "Pancake AIR | Zed NUKE",
    ]
