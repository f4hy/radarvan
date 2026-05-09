"""Compute map stats: player and general win rates by map."""

from collections import defaultdict
from .api_types import (
    General,
    MapData,
    MapGeneralWL,
    MapPlayerWL,
    MapStatsResponse,
    MapSummaryDuration,
    MapSummaryLastWin,
    MapSummaryPlayer,
    MapSummaryPlayerGeneralRecord,
    MapSummaryRanking,
    MapSummaryRecentResult,
    MapSummaryResponse,
    MapSummaryStreak,
    MapSummaryTeamH2H,
    MatchInfo,
    Player,
    Team,
)
from . import replay_files
from .replay_files import map_basename
from . import general_stats as general_stats_module
from .player_ids import resolve_player_name
import logging

RECENT_RESULTS_LIMIT = 5

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
        map_name = map_basename(game.map)
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


def _fmt_player(p: Player) -> str:
    return f"{resolve_player_name(p.name, p.color)}[{p.general.name}]"


def _winners_losers(g: MatchInfo) -> tuple[list[str], list[str]]:
    winners: list[str] = []
    losers: list[str] = []
    for p in g.players:
        if p.team == Team.OBSERVER:
            continue
        (winners if p.team == g.winning_team else losers).append(_fmt_player(p))
    return winners, losers


def _streak_from_results(results_desc: list[bool]) -> int:
    streak = 0
    direction = 0
    for won in results_desc:
        cur = 1 if won else -1
        if direction == 0:
            direction = cur
        elif cur != direction:
            break
        streak += cur
    return streak


def _normalize_map_name(name: str) -> str:
    return "".join(name.split()).lower()


def map_summary(
    games: list[MatchInfo], map_name: str, players: list[MapSummaryPlayer]
) -> MapSummaryResponse:
    normalized = _normalize_map_name(map_name)
    on_map = [
        g
        for g in games
        if _normalize_map_name(map_basename(g.map)) == normalized
        and not g.incomplete
        and g.winning_team >= 1
    ]
    if not on_map:
        return MapSummaryResponse(map_name=map_name, total_games=0)

    request_generals = {p.general for p in players}
    request_resolved = [resolve_player_name(p.name) for p in players]
    request_names = set(request_resolved)

    pg_wl: dict[tuple[str, General], list[int]] = defaultdict(lambda: [0, 0])
    gen_wl: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    player_wl: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    on_map_sorted = sorted(on_map, key=lambda g: g.timestamp, reverse=True)
    player_results_desc: dict[str, list[bool]] = defaultdict(list)
    total_min = 0.0
    min_min = on_map_sorted[0].duration_minutes
    max_min = min_min
    for g in on_map_sorted:
        for p in g.players:
            if p.team == Team.OBSERVER:
                continue
            idx = 0 if p.won else 1
            if p.general in request_generals:
                gen_wl[p.general][idx] += 1
            name = resolve_player_name(p.name, p.color)
            if name in request_names:
                player_wl[name][idx] += 1
                pg_wl[(name, p.general)][idx] += 1
                player_results_desc[name].append(p.won)
        d = g.duration_minutes
        total_min += d
        if d < min_min:
            min_min = d
        if d > max_min:
            max_min = d

    last = on_map_sorted[0]
    last_winners, last_losers = _winners_losers(last)
    last_win = MapSummaryLastWin(
        winners=last_winners, losers=last_losers, date=last.date
    )

    best_general = None
    if gen_wl:
        top_gen = max(gen_wl, key=lambda x: _win_rate(*gen_wl[x]))
        wins, losses = gen_wl[top_gen]
        best_general = MapSummaryRanking(name=top_gen.name, wins=wins, losses=losses)

    best_player = None
    if player_wl:
        top_player = max(player_wl, key=lambda x: _win_rate(*player_wl[x]))
        wins, losses = player_wl[top_player]
        best_player = MapSummaryRanking(name=top_player, wins=wins, losses=losses)

    player_general_records = [
        MapSummaryPlayerGeneralRecord(
            name=resolved,
            general=p.general,
            wins=pg_wl[(resolved, p.general)][0],
            losses=pg_wl[(resolved, p.general)][1],
        )
        for p, resolved in zip(players, request_resolved)
    ]

    duration = MapSummaryDuration(
        avg_minutes=total_min / len(on_map_sorted),
        shortest_minutes=min_min,
        longest_minutes=max_min,
    )

    recent_results = []
    for g in on_map_sorted[:RECENT_RESULTS_LIMIT]:
        winners, losers = _winners_losers(g)
        recent_results.append(
            MapSummaryRecentResult(
                date=g.date,
                winners=winners,
                losers=losers,
                duration_minutes=g.duration_minutes,
            )
        )

    streaks = [
        MapSummaryStreak(name=name, streak=streak)
        for name, streak in (
            (resolved, _streak_from_results(player_results_desc[resolved]))
            for resolved in request_resolved
        )
        if streak != 0
    ]

    team_h2h = _team_h2h(on_map, players)

    return MapSummaryResponse(
        map_name=map_name,
        total_games=len(on_map),
        last_win=last_win,
        best_general=best_general,
        best_player=best_player,
        team_h2h=team_h2h,
        player_general_records=player_general_records,
        duration=duration,
        recent_results=recent_results,
        streaks=streaks,
    )


def _team_h2h(
    on_map: list[MatchInfo], players: list[MapSummaryPlayer]
) -> MapSummaryTeamH2H | None:
    teams: dict[int, list[str]] = defaultdict(list)
    for p in players:
        if p.team >= Team.ONE:
            teams[p.team].append(resolve_player_name(p.name))
    if len(teams) != 2:
        return None
    (_, t1_names), (_, t2_names) = sorted(teams.items())
    t1_set = frozenset(t1_names)
    t2_set = frozenset(t2_names)

    t1_wins = 0
    t2_wins = 0
    for g in on_map:
        match_teams: dict[Team, set[str]] = defaultdict(set)
        for mp in g.players:
            if mp.team == Team.OBSERVER:
                continue
            match_teams[mp.team].add(resolve_player_name(mp.name, mp.color))
        by_set = {frozenset(s): tid for tid, s in match_teams.items()}
        a_id = by_set.get(t1_set)
        b_id = by_set.get(t2_set)
        if a_id is None or b_id is None:
            continue
        if g.winning_team == a_id:
            t1_wins += 1
        elif g.winning_team == b_id:
            t2_wins += 1

    if t1_wins == 0 and t2_wins == 0:
        return None
    return MapSummaryTeamH2H(
        team1=t1_names,
        team2=t2_names,
        team1_wins=t1_wins,
        team2_wins=t2_wins,
    )


def format_map_summary(s: MapSummaryResponse) -> str:
    lines = [f"{s.map_name}: total games={s.total_games}"]
    if s.total_games == 0:
        return "\n".join(lines)
    if s.last_win:
        lines.append(f"last win: {s.last_win}")
    if s.best_general:
        lines.append(
            f"best general: {s.best_general.name} "
            f"({s.best_general.wins}-{s.best_general.losses})"
        )
    if s.best_player:
        lines.append(
            f"best record: {s.best_player.name} "
            f"({s.best_player.wins}-{s.best_player.losses})"
        )
    if s.team_h2h:
        lines.append(
            f"team h2h: [{','.join(s.team_h2h.team1)}] {s.team_h2h.team1_wins}"
            f" - {s.team_h2h.team2_wins} [{','.join(s.team_h2h.team2)}]"
        )
    if s.player_general_records:
        recs = ", ".join(
            f"{r.name}[{r.general.name}] {r.wins}-{r.losses}"
            for r in s.player_general_records
        )
        lines.append(f"player+general on map: {recs}")
    if s.duration:
        lines.append(
            f"duration (min): avg {s.duration.avg_minutes:.1f}, "
            f"shortest {s.duration.shortest_minutes:.1f}, "
            f"longest {s.duration.longest_minutes:.1f}"
        )
    if s.recent_results:
        recent = ";\n".join(
            f"{r.date.strftime('%Y-%m-%d')} W:{','.join(r.winners)} "
            f"L:{','.join(r.losers)} ({r.duration_minutes:.0f}m)"
            for r in s.recent_results
        )
        lines.append(f"\nrecent:\n{recent}\n")
    if s.streaks:
        streak_strs = [
            f"{st.name} {'W' if st.streak > 0 else 'L'}{abs(st.streak)}"
            for st in s.streaks
        ]
        lines.append(f"streaks: {', '.join(streak_strs)}")
    return "\n".join(lines)
