"""Top-N leaderboard statistics (streaks, APM, kills, money, …) computed across
matches."""

import asyncio
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from pydantic import BaseModel

from .api_types import (
    FirstBlood,
    MatchDetails,
    MatchInfo,
    SuperlativeData,
    SuperlativePlayerSummary,
    SuperweaponLaunch,
    Statistic,
)
from .db_utils import DatabaseManager
from .player_ids import HUMAN_NAMES, resolve_player_name
from .player_rating import GameUpset, RatingDailyChange, RatingsAndCounts
from .replay_files import map_basename
from .timeline_events import BASE_SUPERWEAPON_LAUNCHES
import structlog

logger = structlog.get_logger(__name__)


def holds_records(resolved_name: str) -> bool:
    """True if a resolved name is eligible to hold a record.

    A membership test against the known *humans* rather than a blocklist,
    because both things it has to reject are open-ended. AI slots: a
    name-based blocklist of one ("HardArmy") let "Tactical AI" take "Worst
    Record (30d)". Strangers: scraped pickup games pass the competitive filter
    as long as each team has one group member, and two passers-by held
    "Highest APM" and "Fastest to Rank 5". A canonical name outside
    ``HUMAN_NAMES`` is one or the other.
    """
    return resolved_name in HUMAN_NAMES


@dataclass(frozen=True, slots=True)
class StreakRecord:
    count: int
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class PlayerMatchRecord:
    player: str
    value: int
    match_id: int


@dataclass(frozen=True, slots=True)
class ApmRecord:
    player: str
    apm: float
    match_id: int


@dataclass(frozen=True, slots=True)
class ApmTotals:
    total_actions: int
    total_minutes: float
    game_count: int


class Superlatives(BaseModel):
    stats: list[Statistic]
    computed_at: date


def superlative_data_from_details(d: MatchDetails) -> SuperlativeData:
    """Convert a full MatchDetails into the smaller SuperlativeData used by superlatives."""

    def _last_total(key: str) -> int:
        data = d.stats_data.get(key, {})
        if not data:
            return 0
        return sum(data[max(data)].values())

    def _last_per_player(key: str) -> dict[str, int]:
        data = d.stats_data.get(key, {})
        if not data:
            return {}
        return dict(data[max(data)])

    player_summary = [
        SuperlativePlayerSummary(
            name=ps.Name,
            color=ps.Color,
            won=ps.Win,
            money_spent=d.player_money_spent.get(ps.Name, 0),
            units_created_count=sum(v.Count for v in ps.UnitsCreated.values()),
            buildings_built_count=sum(v.Count for v in ps.BuildingsBuilt.values()),
            value_destroyed=(
                sum(v.TotalSpent for v in ps.UnitsDestroyed.values())
                + sum(v.TotalSpent for v in ps.BuildingsDestroyed.values())
            ),
            value_lost=(
                sum(v.TotalSpent for v in ps.UnitsLost.values())
                + sum(v.TotalSpent for v in ps.BuildingsLost.values())
            ),
        )
        for ps in d.player_summary
    ]

    launch_counts: Counter[str] = Counter()
    first_launch: dict[str, SuperweaponLaunch] = {}
    tech_captures: Counter[str] = Counter()
    for e in d.timeline_events:
        if e.event_type == "tech_capture":
            tech_captures[e.player_name] += 1
        elif e.event_type == "superweapon_activated" and any(
            kw in e.event_name for kw in BASE_SUPERWEAPON_LAUNCHES
        ):
            launch_counts[e.player_name] += 1
            prev = first_launch.get(e.player_name)
            if prev is None or e.at_minute < prev.at_minute:
                first_launch[e.player_name] = SuperweaponLaunch(
                    weapon=e.event_name, at_minute=e.at_minute
                )

    winner_players: list[str] | None = None
    loser_players: list[str] | None = None
    winner_min_win_prob: float | None = None
    loser_max_win_prob: float | None = None
    wpot = d.win_prob_over_time
    if wpot is not None and wpot.actual_winner is not None and wpot.points:
        winner_is_a = wpot.actual_winner == "team_a"
        winner_probs = [
            p.prob_team_a if winner_is_a else 1 - p.prob_team_a for p in wpot.points
        ]
        winner_players = wpot.team_a_players if winner_is_a else wpot.team_b_players
        loser_players = wpot.team_b_players if winner_is_a else wpot.team_a_players
        winner_min_win_prob = min(winner_probs)
        loser_max_win_prob = max(1 - p for p in winner_probs)

    return SuperlativeData(
        match_id=d.match_id,
        first_blood=d.first_blood,
        building_first_blood=d.building_first_blood,
        apms=d.apms,
        player_summary=player_summary,
        upgrade_counts={
            player_name: len(upgrades.upgrades)
            for player_name, upgrades in d.upgrade_events.items()
            if upgrades.upgrades
        },
        total_units_killed=_last_total("units_killed"),
        total_buildings_killed=_last_total("buildings_killed"),
        total_xp=_last_total("xp"),
        match_money_spent=sum(d.player_money_spent.values()),
        player_money_collected=d.player_money_collected,
        player_xp_final=_last_per_player("xp"),
        time_to_rank_5=dict(d.time_to_rank_5),
        time_to_search_destroy=dict(d.time_to_search_destroy),
        time_to_hunted=dict(d.time_to_hunted),
        superweapon_launches=dict(launch_counts),
        first_superweapon=first_launch,
        tech_captures=dict(tech_captures),
        winner_players=winner_players,
        loser_players=loser_players,
        winner_min_win_prob=winner_min_win_prob,
        loser_max_win_prob=loser_max_win_prob,
    )


async def load_many_superlative_data(
    match_ids: list[int],
    db_manager: DatabaseManager,
    max_concurrent: int = 2,
    chunk_size: int = 10,
) -> list[SuperlativeData]:
    """Load reduced superlative data for many matches in parallel.

    Each match is loaded as full MatchDetails, immediately converted to the smaller
    SuperlativeData, and the full details discarded - keeping peak memory low.

    Processed in chunks of chunk_size to bound the number of coroutines scheduled at
    once and give Python's GC a chance to release completed batches between chunks.
    """
    # Imported here to break a cycle: match_details depends on this module's
    # SuperlativeData type, and we depend on it for the DB-bound loader.
    from .match_details import load_match_details_threadsafe

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(match_id: int) -> SuperlativeData | None:
        async with semaphore:
            details = await asyncio.to_thread(
                load_match_details_threadsafe, match_id, db_manager
            )
        if details is None:
            return None
        return superlative_data_from_details(details)

    all_results: list[SuperlativeData] = []
    for i in range(0, len(match_ids), chunk_size):
        chunk = match_ids[i : i + chunk_size]
        chunk_results = await asyncio.gather(*[_bounded(mid) for mid in chunk])
        all_results.extend(r for r in chunk_results if r is not None)
    return all_results


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


class ResolvedFirstBlood(NamedTuple):
    """One match's first-blood event with its attacker already alias-resolved.

    Resolving scans the match's player list, so it happens once per match here
    rather than at each of the four places below that need the name.
    """

    data: SuperlativeData
    event: FirstBlood
    attacker: str


def _resolved_first_bloods(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    pick: Callable[[SuperlativeData], FirstBlood | None],
) -> list[ResolvedFirstBlood]:
    """Every match's first blood (unit or building, per ``pick``), attacker
    resolved, excluded players dropped."""
    out: list[ResolvedFirstBlood] = []
    for d in details:
        event = pick(d)
        if event is None:
            continue
        attacker = _resolve_attacker(match_info_by_id, d, event.attacker)
        if not holds_records(attacker):
            continue
        out.append(ResolvedFirstBlood(data=d, event=event, attacker=attacker))
    return out


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


def _extend_streaks(
    current: dict[str, StreakRecord],
    best: dict[str, StreakRecord],
    name: str,
    game_date: date,
) -> None:
    """Continue ``name``'s run through ``game_date``, keeping their best."""
    prev = current.get(name)
    current[name] = (
        StreakRecord(count=1, start=game_date, end=game_date)
        if prev is None
        else StreakRecord(count=prev.count + 1, start=prev.start, end=game_date)
    )
    streak = current[name]
    if name not in best or streak.count > best[name].count:
        best[name] = streak


def get_win_streak_stats(games: list[MatchInfo], computed_at: date) -> list[Statistic]:
    """Longest win streak, longest active streak, and longest losing streak.

    One pass keeps all three: a result that extends the win run is the same
    result that ends the loss run, so they can't be computed independently
    without walking the corpus twice.
    """
    sorted_games = sorted(
        (g for g in games if not g.incomplete), key=lambda g: g.timestamp
    )
    current: dict[str, StreakRecord] = {}
    best: dict[str, StreakRecord] = {}
    current_loss: dict[str, StreakRecord] = {}
    best_loss: dict[str, StreakRecord] = {}
    for game in sorted_games:
        game_date = game.date
        # Competitors only: a spectator's slot has won=False, so watching a
        # game used to book a loss against whoever was casting it.
        for player in game.roster().competitors:
            name = resolve_player_name(player.name, player.color)
            if not holds_records(name):
                continue
            if player.won:
                _extend_streaks(current, best, name, game_date)
                current_loss.pop(name, None)
            else:
                _extend_streaks(current_loss, best_loss, name, game_date)
                current.pop(name, None)
    stats: list[Statistic] = []
    if best:
        top_player = max(best, key=lambda n: best[n].count)
        streak = best[top_player]
        stats.append(
            Statistic(
                stat_name=f"🔥 Longest Win Streak ({streak.start} to {streak.end})",
                date_computed=computed_at,
                value=streak.count,
                player=top_player,
            )
        )
    three_months_ago = datetime.now(UTC).date() - timedelta(days=90)
    recent_current = {n: s for n, s in current.items() if s.end >= three_months_ago}
    if recent_current:
        current_leader = max(recent_current, key=lambda n: recent_current[n].count)
        streak = recent_current[current_leader]
        stats.append(
            Statistic(
                stat_name=f"🔥 Longest Current Streak ({streak.start} to {streak.end})",
                date_computed=computed_at,
                value=streak.count,
                player=current_leader,
            )
        )
    if best_loss:
        worst_player = max(best_loss, key=lambda n: best_loss[n].count)
        streak = best_loss[worst_player]
        stats.append(
            Statistic(
                stat_name=(
                    f"🧊 Longest Losing Streak ({streak.start} to {streak.end})"
                ),
                date_computed=computed_at,
                value=streak.count,
                player=worst_player,
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
            player=map_basename(longest_map),
        ),
        Statistic(
            stat_name="🗺️ Shortest Average Game Map",
            date_computed=computed_at,
            value=_fmt_duration(eligible[shortest_map]),
            player=map_basename(shortest_map),
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


# A night shorter than this is a coin flip, not a run.
MIN_GAME_NIGHT_GAMES = 4

# Enough games together that a pair's record is about the pair rather than one
# lucky evening. 48 pairs clear it in the current corpus.
MIN_DUO_GAMES = 20


def get_attendance_stats(games: list[MatchInfo], computed_at: date) -> list[Statistic]:
    """Who turns up most, and the best undefeated game night anyone has had.

    ``MatchInfo.date`` is already the game-night date (``utils.game_night_date``
    rolls over at 5am Eastern), so a run that ends at 1am counts toward the
    evening it started.
    """
    played: Counter[str] = Counter()
    per_night: dict[tuple[str, date], list[bool]] = defaultdict(list)
    for g in games:
        for p in g.roster().human_participants:
            name = resolve_player_name(p.name, p.color)
            if not holds_records(name):
                continue
            played[name] += 1
            per_night[(name, g.date)].append(p.won)

    stats: list[Statistic] = []
    if played:
        top_name, top_count = played.most_common(1)[0]
        stats.append(
            Statistic(
                stat_name="📊 Most Games Played",
                date_computed=computed_at,
                value=top_count,
                player=top_name,
            )
        )

    perfect = [
        (len(results), night, name)
        for (name, night), results in per_night.items()
        if len(results) >= MIN_GAME_NIGHT_GAMES and all(results)
    ]
    if perfect:
        # Most wins first; a tie goes to whoever got there first.
        wins, night, name = max(perfect, key=lambda p: (p[0], -p[1].toordinal()))
        stats.append(
            Statistic(
                stat_name=f"🌙 Best Game Night ({night})",
                date_computed=computed_at,
                value=f"{wins}-0",
                player=name,
            )
        )
    return stats


def get_duo_stats(games: list[MatchInfo], computed_at: date) -> list[Statistic]:
    """The teammate pairing with the best raw record together.

    Raw wins and losses, not ``player_synergy`` - synergy asks whether a pair
    beats the sum of its parts, which is a different (and less quotable)
    question than who wins most when they are on the same side.
    """
    pair_results: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for g in games:
        by_team: dict[int, list[tuple[str, bool]]] = defaultdict(list)
        for p in g.roster().human_participants:
            name = resolve_player_name(p.name, p.color)
            if not holds_records(name):
                continue
            by_team[p.team].append((name, p.won))
        for members in by_team.values():
            for i, (a, won) in enumerate(members):
                for b, _ in members[i + 1 :]:
                    pair_results[tuple(sorted((a, b)))].append(won)  # type: ignore[index]

    eligible = {
        pair: results
        for pair, results in pair_results.items()
        if len(results) >= MIN_DUO_GAMES
    }
    if not eligible:
        return []
    best = max(eligible, key=lambda pair: sum(eligible[pair]) / len(eligible[pair]))
    results = eligible[best]
    wins = sum(results)
    return [
        Statistic(
            stat_name=f"🤝 Best Duo ({best[0]} & {best[1]})",
            date_computed=computed_at,
            value=f"{wins}-{len(results) - wins}",
        )
    ]


def get_upset_stats(upsets: list[GameUpset], computed_at: date) -> list[Statistic]:
    """The unlikeliest win the rating model has ever been shown.

    ``upsets`` arrives sorted by surprise, so the head is the record. The
    probability shown is the *winners'* pre-game chance.
    """
    if not upsets:
        return []
    top = upsets[0]
    winners = " & ".join(top.winner_players)
    favored = " & ".join(top.favored_players)
    return [
        Statistic(
            stat_name=f"🐍 Biggest Upset ({winners} over {favored})",
            date_computed=computed_at,
            value=f"{top.winner_win_prob * 100:.2f}% to win",
            match_id=top.match_id,
        )
    ]


def get_comeback_stats(
    details: list[SuperlativeData], computed_at: date
) -> list[Statistic]:
    """Biggest comeback and biggest choke, from the sequence model's curve."""
    comeback_candidates = [
        (d, d.winner_min_win_prob)
        for d in details
        if d.winner_min_win_prob is not None
        and d.winner_players
        and all(holds_records(p) for p in d.winner_players)
    ]
    choke_candidates = [
        (d, d.loser_max_win_prob)
        for d in details
        if d.loser_max_win_prob is not None
        and d.loser_players
        and all(holds_records(p) for p in d.loser_players)
    ]
    stats: list[Statistic] = []
    if comeback_candidates:
        best, best_prob = min(comeback_candidates, key=lambda x: x[1])
        winners = " & ".join(best.winner_players or [])
        stats.append(
            Statistic(
                stat_name=f"🔄 Biggest Comeback ({winners})",
                date_computed=computed_at,
                value=f"down to {best_prob * 100:.1f}% to win",
                match_id=best.match_id,
            )
        )
    if choke_candidates:
        worst, worst_prob = max(choke_candidates, key=lambda x: x[1])
        losers = " & ".join(worst.loser_players or [])
        stats.append(
            Statistic(
                stat_name=f"😱 Biggest Choke ({losers})",
                date_computed=computed_at,
                value=f"was at {worst_prob * 100:.1f}% to win",
                match_id=worst.match_id,
            )
        )
    return stats


def get_first_blood_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Stats derived from first blood events across all matches."""
    bloods = _resolved_first_bloods(match_info_by_id, details, lambda d: d.first_blood)
    if not bloods:
        return []

    stats: list[Statistic] = []

    fastest = min(bloods, key=lambda b: b.event.atMinute)
    latest = max(bloods, key=lambda b: b.event.atMinute)
    stats.append(
        Statistic(
            stat_name="🩸 Fastest First Blood",
            date_computed=computed_at,
            value=_fmt_duration(fastest.event.atMinute),
            player=fastest.attacker,
            match_id=fastest.data.match_id,
        )
    )
    stats.append(
        Statistic(
            stat_name="Latest First Blood",
            date_computed=computed_at,
            value=_fmt_duration(latest.event.atMinute),
            player=latest.attacker,
            match_id=latest.data.match_id,
        )
    )

    player_counts: Counter[str] = Counter(b.attacker for b in bloods)
    top_player, top_count = player_counts.most_common(1)[0]
    stats.append(
        Statistic(
            stat_name="🩸 Most First Bloods",
            date_computed=computed_at,
            value=top_count,
            player=top_player,
        )
    )

    return stats


def get_building_first_blood_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Fastest building kill and player with most building first bloods."""
    bfbs = _resolved_first_bloods(
        match_info_by_id, details, lambda d: d.building_first_blood
    )
    if not bfbs:
        return []
    stats: list[Statistic] = []
    fastest = min(bfbs, key=lambda b: b.event.atMinute)
    stats.append(
        Statistic(
            stat_name="💥 Fastest Building First Blood",
            date_computed=computed_at,
            value=_fmt_duration(fastest.event.atMinute),
            player=fastest.attacker,
            match_id=fastest.data.match_id,
        )
    )
    player_counts: Counter[str] = Counter(b.attacker for b in bfbs)
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
    """Match with the highest average APM, best single-match APM, best career rate."""
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

    best: ApmRecord | None = None
    player_totals: dict[str, ApmTotals] = {}
    for d in details:
        color_map = {ps.name: ps.color for ps in d.player_summary}
        for a in d.apms:
            if a.minutes >= 3.0 and a.apm > 0:
                resolved = resolve_player_name(
                    a.player_name, color_map.get(a.player_name, "")
                )
                if not holds_records(resolved):
                    continue
                if best is None or a.apm > best.apm:
                    best = ApmRecord(player=resolved, apm=a.apm, match_id=d.match_id)
                prev = player_totals.get(resolved, ApmTotals(0, 0.0, 0))
                player_totals[resolved] = ApmTotals(
                    total_actions=prev.total_actions + a.action_count,
                    total_minutes=prev.total_minutes + a.minutes,
                    game_count=prev.game_count + 1,
                )
    if best is not None:
        stats.append(
            Statistic(
                stat_name="🚀 Highest APM",
                date_computed=computed_at,
                value=round(best.apm, 1),
                player=best.player,
                match_id=best.match_id,
            )
        )

    MIN_GAMES = 5
    eligible = {
        name: t.total_actions / t.total_minutes
        for name, t in player_totals.items()
        if t.game_count >= MIN_GAMES and t.total_minutes > 0
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
    best_upg: PlayerMatchRecord | None = None
    for d in details:
        color_map = {ps.name: ps.color for ps in d.player_summary}
        for player_name, count in d.upgrade_counts.items():
            if best_upg is None or count > best_upg.value:
                resolved = resolve_player_name(
                    player_name, color_map.get(player_name, "")
                )
                best_upg = PlayerMatchRecord(
                    player=resolved, value=count, match_id=d.match_id
                )
    if best_upg and best_upg.value > 0:
        stats.append(
            Statistic(
                stat_name="🔬 Most Upgrades in a Match",
                date_computed=computed_at,
                value=best_upg.value,
                player=best_upg.player,
                match_id=best_upg.match_id,
            )
        )

    return stats


def _min_candidate(
    current: PlayerMatchRecord | None, value: int, name: str, match_id: int
) -> PlayerMatchRecord | None:
    if value > 0 and (current is None or value < current.value):
        return PlayerMatchRecord(player=name, value=value, match_id=match_id)
    return current


def get_fastest_rank_5_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Fastest player ever to reach generals rank 5 in a single match."""
    fastest: tuple[SuperlativeData, str, float] | None = None
    for d in details:
        for name, minute in d.time_to_rank_5.items():
            resolved = _resolve_attacker(match_info_by_id, d, name)
            if not holds_records(resolved):
                continue
            if fastest is None or minute < fastest[2]:
                fastest = (d, resolved, minute)
    if fastest is None:
        return []
    return [
        Statistic(
            stat_name="🎖️ Fastest to Rank 5",
            date_computed=computed_at,
            value=_fmt_duration(fastest[2]),
            player=fastest[1],
            match_id=fastest[0].match_id,
        )
    ]


def get_fastest_search_destroy_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Fastest activation of USA Search & Destroy battle plan in a single match."""
    fastest: tuple[SuperlativeData, str, float] | None = None
    for d in details:
        for name, minute in d.time_to_search_destroy.items():
            resolved = _resolve_attacker(match_info_by_id, d, name)
            if not holds_records(resolved):
                continue
            if fastest is None or minute < fastest[2]:
                fastest = (d, resolved, minute)
    if fastest is None:
        return []
    return [
        Statistic(
            stat_name="🎯 Fastest Search & Destroy",
            date_computed=computed_at,
            value=_fmt_duration(fastest[2]),
            player=fastest[1],
            match_id=fastest[0].match_id,
        )
    ]


class HuntedOccurrence(NamedTuple):
    """One player going hunted in one match, alias-resolved."""

    data: SuperlativeData
    player: str
    at_minute: float


def _hunted_occurrences(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
) -> list[HuntedOccurrence]:
    """Every (player, match) pair where the player went hunted.

    One entry per player per match - `time_to_hunted` only holds each player's
    *first* hunted flip - so a player who gets hunted, rebuilds a dozer, and
    gets hunted again still counts once.
    """
    out: list[HuntedOccurrence] = []
    for d in details:
        for raw_name, minute in d.time_to_hunted.items():
            resolved = _resolve_attacker(match_info_by_id, d, raw_name)
            if not holds_records(resolved):
                continue
            out.append(HuntedOccurrence(data=d, player=resolved, at_minute=minute))
    return out


def get_hunted_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Who gets production-locked most often.

    "Hunted" is the engine state a player enters when they have no dozer or
    worker left and no way to produce one: they can still fight with what they
    have but cannot rebuild, which is usually decisive in a 1v1.
    """
    occurrences = _hunted_occurrences(match_info_by_id, details)
    if not occurrences:
        return []

    stats: list[Statistic] = []

    player_counts: Counter[str] = Counter(o.player for o in occurrences)
    top_player, top_count = player_counts.most_common(1)[0]
    stats.append(
        Statistic(
            stat_name="🚜 Most Hunted",
            date_computed=computed_at,
            value=top_count,
            player=top_player,
        )
    )

    return stats


def get_superweapon_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Base-superweapon launches: most in one match, and the earliest ever.

    Only the three base-bound superweapons count - see
    ``timeline_events.BASE_SUPERWEAPON_LAUNCHES``. Roughly half the corpus
    carries any, so both records come from the half that does.
    """
    most: PlayerMatchRecord | None = None
    earliest: tuple[SuperlativeData, str, SuperweaponLaunch] | None = None
    for d in details:
        for raw_name, count in d.superweapon_launches.items():
            resolved = _resolve_attacker(match_info_by_id, d, raw_name)
            if not holds_records(resolved):
                continue
            if most is None or count > most.value:
                most = PlayerMatchRecord(
                    player=resolved, value=count, match_id=d.match_id
                )
        for raw_name, launch in d.first_superweapon.items():
            resolved = _resolve_attacker(match_info_by_id, d, raw_name)
            if not holds_records(resolved):
                continue
            if earliest is None or launch.at_minute < earliest[2].at_minute:
                earliest = (d, resolved, launch)

    stats: list[Statistic] = []
    if most is not None:
        stats.append(
            Statistic(
                stat_name="☢️ Most Superweapons Launched",
                date_computed=computed_at,
                value=most.value,
                player=most.player,
                match_id=most.match_id,
            )
        )
    if earliest is not None:
        data, player, launch = earliest
        stats.append(
            Statistic(
                stat_name=f"☢️ Fastest Superweapon Launch ({launch.weapon})",
                date_computed=computed_at,
                value=_fmt_duration(launch.at_minute),
                player=player,
                match_id=data.match_id,
            )
        )
    return stats


def get_tech_capture_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Most tech buildings (oil derricks, hospitals, …) captured in one match."""
    best: PlayerMatchRecord | None = None
    for d in details:
        for raw_name, count in d.tech_captures.items():
            resolved = _resolve_attacker(match_info_by_id, d, raw_name)
            if not holds_records(resolved):
                continue
            if best is None or count > best.value:
                best = PlayerMatchRecord(
                    player=resolved, value=count, match_id=d.match_id
                )
    if best is None:
        return []
    return [
        Statistic(
            stat_name="🛢️ Most Tech Captures",
            date_computed=computed_at,
            value=best.value,
            player=best.player,
            match_id=best.match_id,
        )
    ]


@dataclass(slots=True)
class _XpTotals:
    xp: int = 0
    minutes: float = 0.0
    games: int = 0


def get_xp_rate_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Player with the highest XP-per-minute rate across all matches.

    Eligibility requires at least MIN_GAMES games and a meaningful total play
    time so one fluky short match can't take the top.
    """
    MIN_GAMES = 5
    MIN_MINUTES = 30.0
    totals: dict[str, _XpTotals] = {}
    for d in details:
        match_info = match_info_by_id.get(d.match_id)
        if match_info is None or match_info.duration_minutes <= 0:
            continue
        for name, xp in d.player_xp_final.items():
            if xp <= 0:
                continue
            resolved = _resolve_attacker(match_info_by_id, d, name)
            if not holds_records(resolved):
                continue
            entry = totals.setdefault(resolved, _XpTotals())
            entry.xp += xp
            entry.minutes += match_info.duration_minutes
            entry.games += 1
    eligible = {
        name: t.xp / t.minutes
        for name, t in totals.items()
        if t.games >= MIN_GAMES and t.minutes >= MIN_MINUTES
    }
    if not eligible:
        return []
    top = max(eligible, key=eligible.__getitem__)
    return [
        Statistic(
            stat_name="⭐ Highest XP Rate (per minute)",
            date_computed=computed_at,
            value=round(eligible[top], 1),
            player=top,
        )
    ]


# A win short enough to be a rage-quit says nothing about efficiency. Every
# efficiency record was one before this floor existed: "Fewest Units to Win"
# was 2 units in the same match as "⚡ Shortest 4v4" (2m01s), and "Fewest
# Buildings to Win" was 3 in a 3m36s game. Ten minutes is past the point where
# the loser is still choosing to play.
MIN_EFFICIENCY_MINUTES = 10.0


def get_efficiency_stats(
    match_info_by_id: dict[int, MatchInfo],
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Winning player records: fewest units, fewest buildings, least money spent.

    Restricted to complete wins of at least ``MIN_EFFICIENCY_MINUTES``.
    """
    best_units: PlayerMatchRecord | None = None
    best_buildings: PlayerMatchRecord | None = None
    best_money: PlayerMatchRecord | None = None

    for d in details:
        match_info = match_info_by_id.get(d.match_id)
        if match_info is None or match_info.incomplete:
            continue
        if match_info.duration_minutes < MIN_EFFICIENCY_MINUTES:
            continue
        for ps in d.player_summary:
            if not ps.won:
                continue
            name = resolve_player_name(ps.name, ps.color)
            if not holds_records(name):
                continue
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
                value=best_units.value,
                player=best_units.player,
                match_id=best_units.match_id,
            )
        )
    if best_buildings:
        stats.append(
            Statistic(
                stat_name="Fewest Buildings to Win",
                date_computed=computed_at,
                value=best_buildings.value,
                player=best_buildings.player,
                match_id=best_buildings.match_id,
            )
        )
    if best_money:
        stats.append(
            Statistic(
                stat_name="Least Money to Win",
                date_computed=computed_at,
                value=_fmt_money(best_money.value),
                player=best_money.player,
                match_id=best_money.match_id,
            )
        )
    return stats


def get_money_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Match with the most total money spent.

    There is deliberately no "least spent" counterpart: it read $12,200 across
    a 42-minute 2v2, which is not a frugal game but a replay whose per-player
    `moneySpent` never populated. A floor can't separate the two, so the
    minimum is measuring data coverage rather than play.
    """
    if not details:
        return []

    valued = [(d, d.match_money_spent) for d in details if d.match_money_spent > 0]
    if not valued:
        return []

    most = max(valued, key=lambda x: x[1])

    return [
        Statistic(
            stat_name="💰 Most Money Spent",
            date_computed=computed_at,
            value=_fmt_money(most[1]),
            match_id=most[0].match_id,
        ),
    ]


def get_player_money_stats(
    details: list[SuperlativeData],
    computed_at: date,
) -> list[Statistic]:
    """Top 3 players by career money collected.

    Career money *spent* used to get its own podium beside this one and always
    named the same three players in the same order - you spend what you
    collect, so the two rank identically. One podium says everything both did.
    """
    player_collected: Counter[str] = Counter()

    for d in details:
        color_map = {ps.name: ps.color for ps in d.player_summary}
        for player_name, amount in d.player_money_collected.items():
            resolved = resolve_player_name(player_name, color_map.get(player_name, ""))
            if not holds_records(resolved):
                continue
            player_collected[resolved] += amount

    MEDALS = ["🥇", "🥈", "🥉"]
    return [
        Statistic(
            stat_name=f"💰 Most Money Collected {MEDALS[i]}",
            date_computed=computed_at,
            value=_fmt_money(amount),
            player=name,
        )
        for i, (name, amount) in enumerate(player_collected.most_common(3))
    ]


def get_monthly_stats(
    games: list[MatchInfo],
    daily_changes: dict[str, list[RatingDailyChange]],
    computed_at: date,
) -> list[Statistic]:
    """Best/worst W-L record and biggest rating swing over the last 30 days."""
    thirty_days_ago = computed_at - timedelta(days=30)
    recent_games = [g for g in games if g.date >= thirty_days_ago]

    wl: dict[str, tuple[int, int]] = {}
    for g in recent_games:
        # Competitors only, for the same reason as get_win_streak_stats: a
        # spectator's slot has won=False and would book them a loss.
        for p in g.roster().competitors:
            name = resolve_player_name(p.name, p.color)
            if not holds_records(name):
                continue
            w, l = wl.get(name, (0, 0))
            wl[name] = (w + 1, l) if p.won else (w, l + 1)

    MIN_GAMES = 5
    eligible_wl = {n: (w, l) for n, (w, l) in wl.items() if w + l >= MIN_GAMES}

    stats: list[Statistic] = []

    if eligible_wl:
        best = max(eligible_wl, key=lambda n: eligible_wl[n][0] / sum(eligible_wl[n]))
        worst = min(eligible_wl, key=lambda n: eligible_wl[n][0] / sum(eligible_wl[n]))
        bw, bl = eligible_wl[best]
        ww, worst_losses = eligible_wl[worst]
        stats.append(
            Statistic(
                stat_name="🔥 Best Record (30d)",
                date_computed=computed_at,
                value=f"{bw}-{bl}",
                player=best,
            )
        )
        stats.append(
            Statistic(
                stat_name="❄️ Worst Record (30d)",
                date_computed=computed_at,
                value=f"{ww}-{worst_losses}",
                player=worst,
            )
        )

    monthly_deltas: dict[str, float] = {
        name: sum(c.delta for c in changes if c.date >= thirty_days_ago)
        for name, changes in daily_changes.items()
        if holds_records(name)
    }
    monthly_deltas = {n: d for n, d in monthly_deltas.items() if d != 0.0}

    if monthly_deltas:
        biggest_gain = max(monthly_deltas, key=monthly_deltas.__getitem__)
        biggest_drop = min(monthly_deltas, key=monthly_deltas.__getitem__)
        stats.append(
            Statistic(
                stat_name="📈 Biggest Rating Gain (30d)",
                date_computed=computed_at,
                value=round(monthly_deltas[biggest_gain] * 10),
                player=biggest_gain,
            )
        )
        stats.append(
            Statistic(
                stat_name="📉 Biggest Rating Drop (30d)",
                date_computed=computed_at,
                value=round(monthly_deltas[biggest_drop] * 10),
                player=biggest_drop,
            )
        )

    return stats


def _safe_compute(fn, *args) -> list[Statistic]:  # type: ignore[no-untyped-def]
    try:
        result: list[Statistic] = fn(*args)
        return result
    except Exception:
        logger.exception("error computing superlative stat group", group=fn.__name__)
        return []


def get_superlatives(
    games: list[MatchInfo],
    details: list[SuperlativeData] | None = None,
    ratings: RatingsAndCounts | None = None,
) -> Superlatives:
    """Every record, from the corpus plus whatever derived inputs are available.

    ``ratings`` carries both things the rating pass already computed that a
    record needs (30-day deltas and the upset list); recomputing either here
    would mean a second pass over the corpus. Note that ``ordinal_high`` /
    ``ordinal_low`` are deliberately *not* read - see the rating-privacy note
    in CLAUDE.md.
    """
    computed_at = datetime.now(UTC).date()

    stats: list[Statistic] = [
        *_safe_compute(get_game_count_stats, games, computed_at),
        *_safe_compute(get_win_streak_stats, games, computed_at),
        *_safe_compute(get_map_duration_stats, games, computed_at),
        *_safe_compute(get_match_duration_extremes, games, computed_at),
        *_safe_compute(get_calendar_stats, games, computed_at),
        *_safe_compute(get_attendance_stats, games, computed_at),
        *_safe_compute(get_duo_stats, games, computed_at),
    ]
    if ratings is not None:
        for rating_fn, *rating_args in [
            (get_monthly_stats, games, ratings.daily_changes, computed_at),
            (get_upset_stats, ratings.upsets, computed_at),
        ]:
            stats.extend(_safe_compute(rating_fn, *rating_args))
    if details:
        match_info_by_id = {g.id: g for g in games}
        for fn, *args in [
            (get_first_blood_stats, match_info_by_id, details, computed_at),
            (get_building_first_blood_stats, match_info_by_id, details, computed_at),
            (get_apm_stats, details, computed_at),
            (get_comeback_stats, details, computed_at),
            (get_money_stats, details, computed_at),
            (get_player_money_stats, details, computed_at),
            (get_activity_stats, details, computed_at),
            (get_efficiency_stats, match_info_by_id, details, computed_at),
            (get_fastest_rank_5_stats, match_info_by_id, details, computed_at),
            (get_fastest_search_destroy_stats, match_info_by_id, details, computed_at),
            (get_hunted_stats, match_info_by_id, details, computed_at),
            (get_xp_rate_stats, match_info_by_id, details, computed_at),
            (get_superweapon_stats, match_info_by_id, details, computed_at),
            (get_tech_capture_stats, match_info_by_id, details, computed_at),
        ]:
            stats.extend(_safe_compute(fn, *args))

    return Superlatives(
        stats=stats,
        computed_at=computed_at,
    )
