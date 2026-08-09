"""Compute win/loss records grouped by team composition."""

from collections import defaultdict
from typing import NamedTuple
from .api_types import MatchInfo, TeamRecord, TeamSizeGroup, TeamStatsResponse
from . import game_composition
from .player_ids import resolve_player_name
import structlog


class PlayerResult(NamedTuple):
    name: str
    won: bool


logger = structlog.get_logger(__name__)

MIN_GAMES = 2


def get_team_stats(games: list[MatchInfo]) -> TeamStatsResponse:
    # wl[team_size][team_key] = [wins, losses]
    wl: dict[int, dict[tuple[str, ...], list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )

    for game in games:
        if game.incomplete:
            continue
        if not game_composition.competitive_game_filter(game.composition):
            continue
        if game.winning_team < 1:
            continue

        # Group human players by team number
        teams: dict[int, list[PlayerResult]] = defaultdict(list)
        for player in game.roster().human_participants:
            name = resolve_player_name(player.name, player.color)
            teams[player.team].append(PlayerResult(name=name, won=player.won))

        if not teams:
            continue

        # Only count balanced games (all teams the same size)
        sizes = [len(t) for t in teams.values()]
        if len(set(sizes)) != 1:
            continue
        team_size = sizes[0]
        if team_size < 2 or team_size > 4:
            continue

        for players_with_result in teams.values():
            key = tuple(sorted(pr.name for pr in players_with_result))
            won = players_with_result[0].won
            wl[team_size][key][0 if won else 1] += 1

    groups = []
    for team_size in sorted(wl):
        teams_for_size = [
            TeamRecord(players=list(key), wins=v[0], losses=v[1])
            for key, v in wl[team_size].items()
            if v[0] + v[1] > MIN_GAMES
        ]
        if not teams_for_size:
            continue
        teams_for_size.sort(key=lambda t: t.wins + t.losses, reverse=True)
        groups.append(TeamSizeGroup(size=team_size, teams=teams_for_size))

    logger.info(
        "team stats",
        teams=sum(len(g.teams) for g in groups),
        size_groups=len(groups),
    )
    return TeamStatsResponse(groups=groups)
