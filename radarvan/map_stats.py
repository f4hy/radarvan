"""Compute map stats: player and general win rates by map."""

from collections import defaultdict
from .api_types import (
    General,
    MapData,
    MapGeneralWL,
    MapPlayerWL,
    MapStatsResponse,
    MatchInfo,
)
from . import replay_files
from . import general_stats as general_stats_module
from .player_ids import player_name_map
import logging

logger = logging.getLogger(__name__)

MIN_GAMES = 5
CPU_NAMES = general_stats_module.CPU_NAMES


def get_map_stats(games: list[MatchInfo]) -> MapStatsResponse:
    overall_wl = {
        s.general: s.total
        for s in general_stats_module.get_generals_stats(games).general_stats
    }

    player_wl: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    general_wl: dict[str, dict[int, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    map_games: dict[str, int] = defaultdict(int)

    for game in games:
        if game.incomplete:
            continue
        if not replay_files.path_filter(game.filename):
            continue
        if game.winning_team < 1:
            continue
        map_name = game.map.split("/")[-1] if game.map else "Unknown"
        map_games[map_name] += 1

        for player in game.players:
            if player.name.lower() in CPU_NAMES:
                continue
            if player.general == General.UNRECOGNIZED:
                continue
            name = player_name_map(player.name)
            idx = 0 if player.won else 1
            player_wl[map_name][name][idx] += 1
            general_wl[map_name][player.general.value][idx] += 1

    maps = []
    for map_name, total in sorted(map_games.items(), key=lambda x: -x[1]):
        if total < MIN_GAMES:
            continue
        player_stats = [
            MapPlayerWL(player=p, wins=wl[0], losses=wl[1])
            for p, wl in player_wl[map_name].items()
        ]
        general_stats = []
        for g, wl in general_wl[map_name].items():
            general = General(g)
            map_wr = wl[0] / (wl[0] + wl[1]) if (wl[0] + wl[1]) > 0 else 0.5
            owl = overall_wl.get(general)
            overall_wr = (
                owl.wins / (owl.wins + owl.losses)
                if owl and (owl.wins + owl.losses) > 0
                else 0.5
            )
            general_stats.append(
                MapGeneralWL(
                    general=general,
                    wins=wl[0],
                    losses=wl[1],
                    win_rate_delta=round(map_wr - overall_wr, 4),
                )
            )
        maps.append(
            MapData(
                map_name=map_name,
                total_games=total,
                player_stats=player_stats,
                general_stats=general_stats,
            )
        )

    logger.info(f"map stats: {len(maps)} maps with >= {MIN_GAMES} games")
    return MapStatsResponse(maps=maps)
