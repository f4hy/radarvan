"""One evening of games, reduced to a recap.

Everything here is deterministic and recomputed on request: the night's
records, the formats and maps played, and a handful of highlight cards picked
out of the night's match details. It is the free half of the recap page - the
LLM-written paragraph is generated once a night by the scheduler and simply
attached by the route (see ``commentary/night_summary.py``).

Which games count follows the rest of the app rather than inventing a third
answer: ``match_count`` is every match played that night, while the player
records and most highlights come from the decided *competitive* subset the
caller passes in (``cache.competitive_matches`` - see the "two match sets"
note in CLAUDE.md). A night of comp-stomps therefore shows games played and
no W-L table, which is correct.
"""

from __future__ import annotations

import datetime
from collections import Counter, defaultdict
from typing import NamedTuple

from .api_types import (
    General,
    GameNightHighlight,
    GameNightPlayerLine,
    GameNightRecap,
    MatchDetails,
    MatchInfo,
    Team,
)
from .durations import summarize
from .match_narrative import is_base_superweapon
from .player_ids import resolve_player_name
from .replay_files import map_basename
from .player_rating import GameUpset

# A player who showed up for one game of a twelve-game night is on the sheet,
# but the "best record" card shouldn't be theirs on a 1-0.
MIN_GAMES_FOR_RECORD_CARD = 3

# Card-sized sparkline, not the full curve AIPredictions.tsx renders.
_SPARKLINE_POINTS = 24


def _downsample(values: list[float], n: int) -> list[float]:
    """Evenly stride down to at most n points, always keeping the first and last."""
    if len(values) <= n:
        return values
    last = len(values) - 1
    return [values[round(i * last / (n - 1))] for i in range(n)]


class NightPlayer(NamedTuple):
    """Accumulator for one player's night, before it goes on the wire."""

    wins: list[bool]
    generals: Counter[str]
    apms: list[float]


def _canonical_names(match: MatchInfo) -> dict[str, str]:
    """Raw in-game name -> canonical name for this match's competitors."""
    return {
        slot.name: resolve_player_name(slot.name, slot.color)
        for slot in match.roster().competitors
        if slot.name
    }


def _best_streak(results: list[bool]) -> int:
    best = current = 0
    for won in results:
        current = current + 1 if won else 0
        best = max(best, current)
    return best


def player_lines(
    counted: list[MatchInfo], details_by_id: dict[int, MatchDetails]
) -> list[GameNightPlayerLine]:
    """Per-player records over the night's counted games, best record first.

    ``counted`` must already be in the order the games were played - the
    streak is a run of wins *that night*, so the order is load-bearing.
    Observers never reach this: it iterates ``human_participants``.
    """
    accumulated: dict[str, NightPlayer] = defaultdict(
        lambda: NightPlayer(wins=[], generals=Counter(), apms=[])
    )
    for match in counted:
        details = details_by_id.get(match.id)
        apm_by_raw = (
            {entry.player_name: entry.apm for entry in details.apms} if details else {}
        )
        for slot in match.roster().human_participants:
            name = resolve_player_name(slot.name, slot.color)
            entry = accumulated[name]
            entry.wins.append(slot.won)
            entry.generals[General(slot.general).name] += 1
            apm = apm_by_raw.get(slot.name)
            if apm is not None:
                entry.apms.append(apm)
    lines = [
        GameNightPlayerLine(
            player=name,
            wins=sum(entry.wins),
            losses=len(entry.wins) - sum(entry.wins),
            games=len(entry.wins),
            generals=[general for general, _ in entry.generals.most_common()],
            best_streak=_best_streak(entry.wins),
            best_apm=max(entry.apms) if entry.apms else None,
        )
        for name, entry in accumulated.items()
    ]
    # Most wins first, then fewest losses, then alphabetically - a stable order
    # that reads as a standings table.
    lines.sort(key=lambda line: (-line.wins, line.losses, line.player))
    return lines


def _display_map(match: MatchInfo) -> str:
    """The map as the rest of the app shows it - stored as a path, read as a name."""
    return map_basename(match.map).removesuffix(".map")


def _duration_highlights(counted: list[MatchInfo]) -> list[GameNightHighlight]:
    if not counted:
        return []
    longest = max(counted, key=lambda m: m.duration_minutes)
    shortest = min(counted, key=lambda m: m.duration_minutes)
    highlights = [
        GameNightHighlight(
            kind="longest_game",
            title="Longest game",
            detail=f"{longest.duration_minutes:.1f} min on {_display_map(longest)}",
            match_id=longest.id,
        )
    ]
    if shortest.id != longest.id:
        highlights.append(
            GameNightHighlight(
                kind="shortest_game",
                title="Shortest game",
                detail=f"{shortest.duration_minutes:.1f} min on {_display_map(shortest)}",
                match_id=shortest.id,
            )
        )
    return highlights


def _upset_highlight(
    counted: list[MatchInfo], upsets: list[GameUpset]
) -> list[GameNightHighlight]:
    """The night's unlikeliest win, as the rating model saw it beforehand.

    Worded as a *projection* on purpose. The number is ``player_rating``'s
    pre-game estimate - not an observed frequency and not a fact about the
    players. The model is a rating system fitted to this group's own games and
    it is wrong regularly, so a flat "30% to win" reads as a harder claim than
    the data supports.

    A probability, never a rating level - see the ratings note in CLAUDE.md.
    ``upsets`` is the whole corpus's list (the rating model only produces it
    that way); it is narrowed to this night here.
    """
    night_ids = {match.id for match in counted}
    tonight = [upset for upset in upsets if upset.match_id in night_ids]
    if not tonight:
        return []
    top = max(tonight, key=lambda upset: upset.surprise)
    winners = " & ".join(top.winner_players)
    favored = " & ".join(top.favored_players)
    return [
        GameNightHighlight(
            kind="upset",
            title="Biggest upset",
            detail=(
                f"{winners} beat {favored} - our model projected them "
                f"{top.winner_win_prob * 100:.0f}% to win"
            ),
            match_id=top.match_id,
        )
    ]


def _detail_highlights(
    counted: list[MatchInfo], details_by_id: dict[int, MatchDetails]
) -> list[GameNightHighlight]:
    """Highlights that need the parsed replay: first blood, APM, superweapons, collapses, momentum."""
    highlights: list[GameNightHighlight] = []
    fastest_blood: tuple[float, str, int] | None = None
    best_apm: tuple[float, str, int] | None = None
    launches: Counter[str] = Counter()
    first_launch: tuple[float, str, str, int] | None = None
    powers: Counter[str] = Counter()
    hunted: list[tuple[float, str, int]] = []
    best_momentum: tuple[float, list[str], list[float], int] | None = None

    for match in counted:
        details = details_by_id.get(match.id)
        if details is None:
            continue
        canonical = _canonical_names(match)
        wpot = details.win_prob_over_time
        if wpot is not None and wpot.actual_winner is not None and wpot.points:
            winner_is_a = wpot.actual_winner == "team_a"
            winner_probs = [
                p.prob_team_a if winner_is_a else 1 - p.prob_team_a for p in wpot.points
            ]
            winner_names = wpot.team_a_players if winner_is_a else wpot.team_b_players
            min_prob = min(winner_probs)
            if best_momentum is None or min_prob < best_momentum[0]:
                best_momentum = (min_prob, winner_names, winner_probs, match.id)
        blood = details.first_blood
        if blood is not None:
            attacker = canonical.get(blood.attacker, blood.attacker)
            if fastest_blood is None or blood.atMinute < fastest_blood[0]:
                fastest_blood = (blood.atMinute, attacker, match.id)
        for entry in details.apms:
            name = canonical.get(entry.player_name, entry.player_name)
            if best_apm is None or entry.apm > best_apm[0]:
                best_apm = (entry.apm, name, match.id)
        for event in details.timeline_events:
            if event.event_type != "superweapon_activated":
                continue
            name = canonical.get(event.player_name, event.player_name)
            # The engine tags several generals-panel powers "Superweapon*" too,
            # so this split is what stops a Spectre Gunship being reported as a
            # superweapon launch - see match_narrative.is_base_superweapon.
            if not is_base_superweapon(event.event_name):
                powers[name] += 1
                continue
            launches[name] += 1
            if first_launch is None or event.at_minute < first_launch[0]:
                first_launch = (event.at_minute, name, event.event_name, match.id)
        for raw, minute in details.time_to_hunted.items():
            hunted.append((minute, canonical.get(raw, raw), match.id))

    if fastest_blood is not None:
        minute, name, match_id = fastest_blood
        highlights.append(
            GameNightHighlight(
                kind="first_blood",
                title="Fastest first blood",
                detail=f"{name} at {minute:.1f} min",
                match_id=match_id,
            )
        )
    if best_apm is not None:
        rate, name, match_id = best_apm
        highlights.append(
            GameNightHighlight(
                kind="apm",
                title="Fastest hands",
                detail=f"{name} at {rate:.0f} APM",
                match_id=match_id,
            )
        )
    if first_launch is not None:
        minute, name, weapon, match_id = first_launch
        highlights.append(
            GameNightHighlight(
                kind="superweapon",
                title="First superweapon",
                # "launched"/"called in" match the narrative's verbs, so the
                # two surfaces don't describe the same event differently.
                detail=f"{name} launched {weapon} at {minute:.1f} min",
                match_id=match_id,
            )
        )
    if launches:
        name, count = launches.most_common(1)[0]
        if count > 1:
            highlights.append(
                GameNightHighlight(
                    kind="superweapon",
                    title="Most superweapons",
                    detail=f"{name} launched {count}",
                )
            )
    if powers:
        name, count = powers.most_common(1)[0]
        if count > 1:
            highlights.append(
                GameNightHighlight(
                    kind="power",
                    title="Most generals powers",
                    detail=f"{name} called in {count}",
                )
            )
    if hunted:
        minute, name, match_id = min(hunted, key=lambda item: item[0])
        highlights.append(
            GameNightHighlight(
                kind="hunted",
                title="Earliest collapse",
                detail=f"{name} went hunted at {minute:.1f} min",
                match_id=match_id,
            )
        )
    if best_momentum is not None:
        min_prob, winner_names, winner_probs, match_id = best_momentum
        winners = " & ".join(winner_names)
        highlights.append(
            GameNightHighlight(
                kind="momentum",
                title="Wildest swing",
                detail=f"{winners} fell to {min_prob * 100:.0f}% to win before taking it",
                match_id=match_id,
                points=_downsample(winner_probs, _SPARKLINE_POINTS),
            )
        )
    return highlights


def _record_highlight(lines: list[GameNightPlayerLine]) -> list[GameNightHighlight]:
    eligible = [line for line in lines if line.games >= MIN_GAMES_FOR_RECORD_CARD]
    if not eligible:
        return []
    best = max(eligible, key=lambda line: (line.wins / line.games, line.games))
    worst = min(eligible, key=lambda line: (line.wins / line.games, -line.games))
    highlights = [
        GameNightHighlight(
            kind="best_record",
            title="Best of the night",
            detail=f"{best.player} went {best.wins}-{best.losses}",
        )
    ]
    if worst.player != best.player:
        highlights.append(
            GameNightHighlight(
                kind="worst_record",
                title="Rough night",
                detail=f"{worst.player} went {worst.wins}-{worst.losses}",
            )
        )
    return highlights


def _format_of(match: MatchInfo) -> str:
    composition = match.composition
    if composition is None:
        return "Unknown"
    return "FFA" if composition.is_ffa else composition.category


def build_recap(
    night: datetime.date,
    all_matches: list[MatchInfo],
    counted: list[MatchInfo],
    details_by_id: dict[int, MatchDetails],
    upsets: list[GameUpset],
) -> GameNightRecap:
    """Assemble the deterministic half of the recap.

    ``all_matches`` is every match of the night (what "12 games" means);
    ``counted`` is the decided competitive subset the records are computed
    over. Both must be sorted by the time they were played.
    """
    decided = [match for match in counted if match.winning_team > Team.NONE]
    lines = player_lines(decided, details_by_id)
    durations = summarize([match.duration_minutes for match in all_matches])
    started = min((match.timestamp for match in all_matches), default=None)
    ended = max(
        (
            match.timestamp + datetime.timedelta(minutes=match.duration_minutes)
            for match in all_matches
        ),
        default=None,
    )
    return GameNightRecap(
        date=night,
        match_count=len(all_matches),
        counted_matches=len(decided),
        total_minutes=durations.total_minutes,
        median_minutes=durations.median_minutes,
        started_at=started,
        ended_at=ended,
        formats=dict(Counter(_format_of(m) for m in all_matches).most_common()),
        maps=dict(Counter(_display_map(m) for m in all_matches).most_common()),
        players=lines,
        highlights=[
            *_record_highlight(lines),
            *_upset_highlight(decided, upsets),
            *_duration_highlights(decided or all_matches),
            *_detail_highlights(decided, details_by_id),
        ],
    )
