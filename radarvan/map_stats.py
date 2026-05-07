"""Compute map stats: player and general win rates by map."""

from collections import defaultdict
from collections.abc import Sequence
from .api_types import (
    General,
    MapData,
    MapGeneralWL,
    MapPlayerWL,
    MapStatsResponse,
    MapSummaryPlayer,
    MatchInfo,
    Player,
    Team,
)
from . import replay_files
from . import general_stats as general_stats_module
from .player_ids import resolve_player_name
import logging

logger = logging.getLogger(__name__)

MIN_GAMES = 5


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
            if player.team == Team.OBSERVER:
                continue
            name = resolve_player_name(player.name, player.color)
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


def _win_rate(wins: int, losses: int) -> float:
    total = wins + losses
    return wins / total if total > 0 else 0.0


def map_summary(games: list[MatchInfo], map_name: str, players: list[MapSummaryPlayer]) -> str:
    on_map = [
        g for g in games
        if g.map.split("/")[-1] == map_name and not g.incomplete and g.winning_team >= 1
    ]
    if not on_map:
        return f"No recorded games on {map_name}."

    lines: list[str] = []

    # Last win
    last = max(on_map, key=lambda g: g.timestamp)
    winning_players = [
        p for p in last.players if p.team == last.winning_team
    ]
    losing_players = [
        p for p in last.players if p.team != last.winning_team and p.team != Team.OBSERVER
    ]
    def fmt_team(ps: Sequence[Player]) -> str:
        return ", ".join(f"{resolve_player_name(p.name, p.color)}[{p.general.name}]" for p in ps)
    lines.append(
        f"Last win on {map_name}: {fmt_team(winning_players)} beat {fmt_team(losing_players)}"
        f" on {last.date}"
    )

    # General win rates among the requested generals
    request_generals = {p.general for p in players}
    gen_wl: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    for g in on_map:
        for p in g.players:
            if p.team == Team.OBSERVER:
                continue
            if p.general in request_generals:
                gen_wl[p.general][0 if p.won else 1] += 1

    if gen_wl:
        best_gen = max(gen_wl, key=lambda g: _win_rate(*gen_wl[g]))
        w, l = gen_wl[best_gen]
        lines.append(
            f"Best general on this map (from today's pool): {best_gen.name}"
            f" ({w}W-{l}L, {_win_rate(w, l):.0%})"
        )

    # Player win rates among the requested players
    request_names = {resolve_player_name(p.name) for p in players}
    player_wl: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for g in on_map:
        for p in g.players:
            if p.team == Team.OBSERVER:
                continue
            name = resolve_player_name(p.name, p.color)
            if name in request_names:
                player_wl[name][0 if p.won else 1] += 1

    if player_wl:
        best_player = max(player_wl, key=lambda n: _win_rate(*player_wl[n]))
        w, l = player_wl[best_player]
        lines.append(
            f"Best player on this map (from today's pool): {best_player}"
            f" ({w}W-{l}L, {_win_rate(w, l):.0%})"
        )

    return "\n".join(lines)
