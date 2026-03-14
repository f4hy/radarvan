from collections import Counter
from datetime import date
from pydantic import BaseModel

from .api_types import (
    MatchInfo,
    SuperlativeData,
    Statistic,
)
from .player_ids import resolve_player_name
import logging

logger = logging.getLogger(__name__)


class Superlatives(BaseModel):
    stats: list[Statistic]
    computed_at: date


def get_game_count_stats(games: list[MatchInfo], computed_at: date) -> list[Statistic]:
    """Total game counts broken down by format."""
    stats = [
        Statistic(stat_name="Total Games", date_computed=computed_at, value=len(games))
    ]
    for team_size in (2, 3, 4):
        category = f"{team_size}v{team_size}"
        count = sum(
            1
            for g in games
            if g.composition is not None and g.composition.category == category
        )
        if count:
            stats.append(
                Statistic(
                    stat_name=f"{category} Games",
                    date_computed=computed_at,
                    value=count,
                )
            )
    return stats


def _fmt_duration(minutes: float) -> str:
    total_seconds = int(minutes * 60)
    return f"{total_seconds // 60}m {total_seconds % 60:02d}s"


def get_match_duration_extremes(
    games: list[MatchInfo], computed_at: date
) -> list[Statistic]:
    """Longest and shortest complete match for each of 2v2, 3v3, and 4v4."""
    stats: list[Statistic] = []
    for team_size in (2, 3, 4):
        category = f"{team_size}v{team_size}"
        eligible = [
            g
            for g in games
            if g.composition is not None
            and g.composition.category == category
            and not g.incomplete
        ]
        if not eligible:
            continue
        longest = max(eligible, key=lambda g: g.duration_minutes)
        shortest = min(eligible, key=lambda g: g.duration_minutes)
        stats.append(
            Statistic(
                stat_name=f"⏳ Longest {category}",
                date_computed=computed_at,
                value=_fmt_duration(longest.duration_minutes),
                match_id=longest.id,
            )
        )
        stats.append(
            Statistic(
                stat_name=f"⚡ Shortest {category}",
                date_computed=computed_at,
                value=_fmt_duration(shortest.duration_minutes),
                match_id=shortest.id,
            )
        )
    return stats


def _resolve_attacker(
    match_info_by_id: dict[int, MatchInfo], d: SuperlativeData, attacker: str
) -> str:
    match_info = match_info_by_id.get(d.match_id)
    if match_info is None:
        return resolve_player_name(attacker)
    for p in match_info.players:
        if p.name == attacker:
            return resolve_player_name(attacker, p.color)
    return resolve_player_name(attacker)


def get_win_streak_stats(games: list[MatchInfo], computed_at: date) -> list[Statistic]:
    """All-time longest win streak and current longest active streak."""
    sorted_games = sorted(
        (g for g in games if not g.incomplete), key=lambda g: g.timestamp
    )
    # (count, start_date, last_win_date)
    current: dict[str, tuple[int, date, date]] = {}
    best: dict[str, tuple[int, date, date]] = {}
    for game in sorted_games:
        game_date = game.date
        for player in game.players:
            name = resolve_player_name(player.name, player.color)
            if player.won:
                prev = current.get(name)
                current[name] = (
                    (1, game_date, game_date)
                    if prev is None
                    else (prev[0] + 1, prev[1], game_date)
                )
                count, start, end = current[name]
                if name not in best or count > best[name][0]:
                    best[name] = (count, start, end)
            else:
                current.pop(name, None)
    stats: list[Statistic] = []
    if best:
        top_player = max(best, key=lambda n: best[n][0])
        count, start, end = best[top_player]
        stats.append(
            Statistic(
                stat_name=f"🔥 Longest Win Streak ({start} to {end})",
                date_computed=computed_at,
                value=count,
                player=top_player,
            )
        )
    if current:
        current_leader = max(current, key=lambda n: current[n][0])
        count, start, end = current[current_leader]
        stats.append(
            Statistic(
                stat_name=f"🔥 Longest Current Streak ({start} to {end})",
                date_computed=computed_at,
                value=count,
                player=current_leader,
            )
        )
    return stats


def get_map_duration_stats(
    games: list[MatchInfo], computed_at: date
) -> list[Statistic]:
    """Maps with the longest and shortest average game duration (min 3 complete games)."""
    map_durations: dict[str, list[float]] = {}
    for g in games:
        if not g.incomplete:
            map_durations.setdefault(g.map, []).append(g.duration_minutes)
    MIN_GAMES = 3
    eligible = {
        m: sum(ds) / len(ds) for m, ds in map_durations.items() if len(ds) >= MIN_GAMES
    }
    if not eligible:
        return []
    longest_map = max(eligible, key=eligible.__getitem__)
    shortest_map = min(eligible, key=eligible.__getitem__)
    return [
        Statistic(
            stat_name="🗺️ Longest Average Game Map",
            date_computed=computed_at,
            value=_fmt_duration(eligible[longest_map]),
            player=longest_map.split("/")[-1],
        ),
        Statistic(
            stat_name="🗺️ Shortest Average Game Map",
            date_computed=computed_at,
            value=_fmt_duration(eligible[shortest_map]),
            player=shortest_map.split("/")[-1],
        ),
    ]


def get_calendar_stats(games: list[MatchInfo], computed_at: date) -> list[Statistic]:
    """Busiest single day and longest break between sessions."""
    if not games:
        return []
    stats: list[Statistic] = []
    date_counts: Counter[date] = Counter(g.date for g in games)
    busiest_date, busiest_count = date_counts.most_common(1)[0]
    stats.append(
        Statistic(
            stat_name="Most Matches in a Day",
            date_computed=computed_at,
            value=f"{busiest_count} ({busiest_date})",
        )
    )
    return stats


def get_first_blood_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Stats derived from first blood events across all matches."""
    bloods = [(d, d.first_blood) for d in details if d.first_blood is not None]
    if not bloods:
        return []

    stats: list[Statistic] = []

    fastest = min(bloods, key=lambda x: x[1].atMinute)
    latest = max(bloods, key=lambda x: x[1].atMinute)
    stats.append(
        Statistic(
            stat_name="🩸 Fastest First Blood",
            date_computed=computed_at,
            value=_fmt_duration(fastest[1].atMinute),
            player=_resolve_attacker(match_info_by_id, fastest[0], fastest[1].attacker),
            match_id=fastest[0].match_id,
        )
    )
    stats.append(
        Statistic(
            stat_name="Latest First Blood",
            date_computed=computed_at,
            value=_fmt_duration(latest[1].atMinute),
            player=_resolve_attacker(match_info_by_id, latest[0], latest[1].attacker),
            match_id=latest[0].match_id,
        )
    )

    player_counts: Counter[str] = Counter(
        _resolve_attacker(match_info_by_id, d, fb.attacker) for d, fb in bloods
    )
    top_player, top_count = player_counts.most_common(1)[0]
    stats.append(
        Statistic(
            stat_name="🩸 Most First Bloods",
            date_computed=computed_at,
            value=top_count,
            player=top_player,
        )
    )

    general_counts: Counter[str] = Counter()
    for d, fb in bloods:
        match_info = match_info_by_id.get(d.match_id)
        if match_info is None:
            continue
        for p in match_info.players:
            if resolve_player_name(p.name, p.color) == _resolve_attacker(
                match_info_by_id, d, fb.attacker
            ):
                general_counts[p.general.name] += 1
                break
    if general_counts:
        top_general, gen_count = general_counts.most_common(1)[0]
        stats.append(
            Statistic(
                stat_name="Most First Bloods by General",
                date_computed=computed_at,
                value=gen_count,
                player=top_general,
            )
        )

    return stats


def get_building_first_blood_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Fastest building kill and player with most building first bloods."""
    bfbs = [
        (d, d.building_first_blood)
        for d in details
        if d.building_first_blood is not None
    ]
    if not bfbs:
        return []
    stats: list[Statistic] = []
    fastest = min(bfbs, key=lambda x: x[1].atMinute)
    stats.append(
        Statistic(
            stat_name="💥 Fastest Building First Blood",
            date_computed=computed_at,
            value=_fmt_duration(fastest[1].atMinute),
            player=_resolve_attacker(match_info_by_id, fastest[0], fastest[1].attacker),
            match_id=fastest[0].match_id,
        )
    )
    player_counts: Counter[str] = Counter(
        _resolve_attacker(match_info_by_id, d, bfb.attacker) for d, bfb in bfbs
    )
    top_player, top_count = player_counts.most_common(1)[0]
    stats.append(
        Statistic(
            stat_name="Most Building First Bloods",
            date_computed=computed_at,
            value=top_count,
            player=top_player,
        )
    )
    return stats


def _fmt_money(amount: int) -> str:
    return f"${amount:,}"


def get_apm_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Match with highest average APM and player with highest APM."""
    if not details:
        return []

    stats: list[Statistic] = []

    def _avg_apm(d: SuperlativeData) -> float:
        apms = [a.apm for a in d.apms if a.apm > 0 and a.minutes >= 1.0]
        return sum(apms) / len(apms) if apms else 0.0

    best_match, avg = max(((d, _avg_apm(d)) for d in details), key=lambda x: x[1])
    if avg > 0:
        stats.append(
            Statistic(
                stat_name="Highest Average APM Match",
                date_computed=computed_at,
                value=round(avg, 1),
                match_id=best_match.match_id,
            )
        )

    best: tuple[str, float, int] | None = None  # (player_name, apm, match_id)
    # player -> (total_actions, total_minutes, game_count)
    player_totals: dict[str, tuple[int, float, int]] = {}
    for d in details:
        color_map = {ps.name: ps.color for ps in d.player_summary}
        for a in d.apms:
            if a.minutes >= 3.0 and a.apm > 0:
                resolved = resolve_player_name(
                    a.player_name, color_map.get(a.player_name, "")
                )
                if best is None or a.apm > best[1]:
                    best = (resolved, a.apm, d.match_id)
                prev_actions, prev_minutes, prev_games = player_totals.get(
                    resolved, (0, 0.0, 0)
                )
                player_totals[resolved] = (
                    prev_actions + a.action_count,
                    prev_minutes + a.minutes,
                    prev_games + 1,
                )
    if best is not None:
        stats.append(
            Statistic(
                stat_name="🚀 Highest APM",
                date_computed=computed_at,
                value=round(best[1], 1),
                player=best[0],
                match_id=best[2],
            )
        )

    MIN_GAMES = 5
    eligible = {
        name: total_actions / total_minutes
        for name, (total_actions, total_minutes, game_count) in player_totals.items()
        if game_count >= MIN_GAMES and total_minutes > 0
    }
    if eligible:
        top_name = max(eligible, key=eligible.__getitem__)
        stats.append(
            Statistic(
                stat_name="🚀 Highest Average APM Overall",
                date_computed=computed_at,
                value=round(eligible[top_name], 1),
                player=top_name,
            )
        )

    return stats


def get_activity_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Most units killed, buildings destroyed, XP earned, and upgrades by one player."""
    if not details:
        return []

    stats: list[Statistic] = []

    # Most units killed total in a match
    best_uk, uk_count = max(
        ((d, d.total_units_killed) for d in details),
        key=lambda x: x[1],
    )
    if uk_count > 0:
        stats.append(
            Statistic(
                stat_name="💀 Most Units Killed",
                date_computed=computed_at,
                value=uk_count,
                match_id=best_uk.match_id,
            )
        )

    # Most buildings destroyed total in a match
    best_bk, bk_count = max(
        ((d, d.total_buildings_killed) for d in details),
        key=lambda x: x[1],
    )
    if bk_count > 0:
        stats.append(
            Statistic(
                stat_name="🏚️ Most Buildings Destroyed",
                date_computed=computed_at,
                value=bk_count,
                match_id=best_bk.match_id,
            )
        )

    # Most XP earned total in a match
    best_xp, xp_total = max(
        ((d, d.total_xp) for d in details),
        key=lambda x: x[1],
    )
    if xp_total > 0:
        stats.append(
            Statistic(
                stat_name="⭐ Most XP Earned",
                date_computed=computed_at,
                value=xp_total,
                match_id=best_xp.match_id,
            )
        )

    # Most upgrades purchased by a single player in any match
    best_upg: tuple[str, int, int] | None = None  # (player_name, count, match_id)
    for d in details:
        color_map = {ps.name: ps.color for ps in d.player_summary}
        for player_name, count in d.upgrade_counts.items():
            if best_upg is None or count > best_upg[1]:
                resolved = resolve_player_name(
                    player_name, color_map.get(player_name, "")
                )
                best_upg = (resolved, count, d.match_id)
    if best_upg and best_upg[1] > 0:
        stats.append(
            Statistic(
                stat_name="🔬 Most Upgrades in a Match",
                date_computed=computed_at,
                value=best_upg[1],
                player=best_upg[0],
                match_id=best_upg[2],
            )
        )

    return stats


def _min_candidate(
    current: tuple[str, int, int] | None, value: int, name: str, match_id: int
) -> tuple[str, int, int] | None:
    if value > 0 and (current is None or value < current[1]):
        return (name, value, match_id)
    return current


def get_efficiency_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Winning player records: fewest units, fewest buildings, least money spent."""
    best_units: tuple[str, int, int] | None = None  # (player, count, match_id)
    best_buildings: tuple[str, int, int] | None = None
    best_money: tuple[str, int, int] | None = None

    for d in details:
        for ps in d.player_summary:
            if not ps.won:
                continue
            name = resolve_player_name(ps.name, ps.color)
            best_units = _min_candidate(
                best_units,
                ps.units_created_count,
                name,
                d.match_id,
            )
            best_buildings = _min_candidate(
                best_buildings,
                ps.buildings_built_count,
                name,
                d.match_id,
            )
            best_money = _min_candidate(best_money, ps.money_spent, name, d.match_id)

    stats: list[Statistic] = []
    if best_units:
        stats.append(
            Statistic(
                stat_name="Fewest Units to Win",
                date_computed=computed_at,
                value=best_units[1],
                player=best_units[0],
                match_id=best_units[2],
            )
        )
    if best_buildings:
        stats.append(
            Statistic(
                stat_name="Fewest Buildings to Win",
                date_computed=computed_at,
                value=best_buildings[1],
                player=best_buildings[0],
                match_id=best_buildings[2],
            )
        )
    if best_money:
        stats.append(
            Statistic(
                stat_name="Least Money to Win",
                date_computed=computed_at,
                value=_fmt_money(best_money[1]),
                player=best_money[0],
                match_id=best_money[2],
            )
        )
    return stats


def get_money_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Match with most and least total money spent."""
    if not details:
        return []

    valued = [(d, d.match_money_spent) for d in details if d.match_money_spent > 0]
    if not valued:
        return []

    most = max(valued, key=lambda x: x[1])
    least = min(valued, key=lambda x: x[1])

    return [
        Statistic(
            stat_name="💰 Most Money Spent",
            date_computed=computed_at,
            value=_fmt_money(most[1]),
            match_id=most[0].match_id,
        ),
        Statistic(
            stat_name="Least Money Spent",
            date_computed=computed_at,
            value=_fmt_money(least[1]),
            match_id=least[0].match_id,
        ),
    ]


def get_player_money_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Top 3 players by total money collected and total money spent across all games."""
    player_collected: Counter[str] = Counter()
    player_spent: Counter[str] = Counter()

    for d in details:
        color_map = {ps.name: ps.color for ps in d.player_summary}

        for player_name, amount in d.player_money_collected.items():
            resolved = resolve_player_name(player_name, color_map.get(player_name, ""))
            player_collected[resolved] += amount

        for ps in d.player_summary:
            if ps.money_spent <= 0:
                continue
            player_spent[resolve_player_name(ps.name, ps.color)] += ps.money_spent

    MEDALS = ["🥇", "🥈", "🥉"]
    stats: list[Statistic] = []

    for i, (name, amount) in enumerate(player_collected.most_common(3)):
        stats.append(
            Statistic(
                stat_name=f"💰 Most Money Collected {MEDALS[i]}",
                date_computed=computed_at,
                value=_fmt_money(amount),
                player=name,
            )
        )

    for i, (name, amount) in enumerate(player_spent.most_common(3)):
        stats.append(
            Statistic(
                stat_name=f"💸 Most Money Spent Overall {MEDALS[i]}",
                date_computed=computed_at,
                value=_fmt_money(amount),
                player=name,
            )
        )

    return stats


def _safe_compute(fn, *args) -> list[Statistic]:  # type: ignore[no-untyped-def]
    try:
        result: list[Statistic] = fn(*args)
        return result
    except Exception:
        logger.exception(f"Error computing superlative stat group {fn.__name__}")
        return []


def get_superlatives(
    games: list[MatchInfo], details: list[SuperlativeData] | None = None
) -> Superlatives:
    computed_at = date.today()

    stats: list[Statistic] = [
        *_safe_compute(get_game_count_stats, games, computed_at),
        *_safe_compute(get_win_streak_stats, games, computed_at),
        *_safe_compute(get_map_duration_stats, games, computed_at),
        *_safe_compute(get_match_duration_extremes, games, computed_at),
        *_safe_compute(get_calendar_stats, games, computed_at),
    ]
    if details:
        match_info_by_id = {g.id: g for g in games}
        for fn, *args in [
            (get_first_blood_stats, match_info_by_id, details, computed_at),
            (get_building_first_blood_stats, match_info_by_id, details, computed_at),
            (get_apm_stats, details, computed_at),
            (get_money_stats, details, computed_at),
            (get_player_money_stats, details, computed_at),
            (get_activity_stats, details, computed_at),
            (get_efficiency_stats, details, computed_at),
        ]:
            stats.extend(_safe_compute(fn, *args))

    return Superlatives(
        stats=stats,
        computed_at=computed_at,
    )
