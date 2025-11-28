"""Computer player stats."""

"""Get match info from a replay.
"""

from api_types import (
    MatchInfo,
    General,
    PlayerStats,
    PlayerStat,
    WinLoss,
)
import logging

logger = logging.getLogger(__name__)


def player_name_map(name: str) -> str:
    """Map all aliases"""

    mapping = {
        "skip": "Skip",
        "mod": "Modus",
        "131": "OneThree111",
        "neo": "Neo",
        "pan": "Pancake",
        "pc": "Pancake",
        "wld": "WildCard",
        "wild": "WildCard",
        "wildcard": "WildCard",
        "cd": "CoreDawg",
        "syn": "Syn",
        "stm": "STM",
        "ty": "Tytan",
        "tyt": "Tytan",
        "pcap": "pcap",
        "grn": "Gorn",
    }
    return mapping.get(name.lower(), name)


def total_games(player_stat: PlayerStat) -> int:
    return sum(wl.wins + wl.losses for wl in player_stat.stats.values())


def get_player_stats(games: list[MatchInfo]) -> PlayerStats:
    player_stats: dict[str, PlayerStat] = {}

    for game in games:
        if game.incomplete:
            continue
        for player in game.players:
            name = player_name_map(player.name)
            if name not in player_stats:
                player_stats[name] = PlayerStat(
                    player_name=name,
                    stats={General(i): WinLoss(wins=0, losses=0) for i in range(12)},
                    faction_stats=[],
                    over_time=[],
                )
            if player.general == General.UNRECOGNIZED:
                continue
            logger.info(f"adding {player.general=} win for {game.winning_team}")
            if player.team == game.winning_team:
                player_stats[name].stats[player.general].wins += 1
            else:
                player_stats[name].stats[player.general].losses += 1

    filtered = [stat for stat in player_stats.values() if total_games(stat) > 4]

    return PlayerStats(player_stats=sorted(filtered, key=total_games, reverse=True))
