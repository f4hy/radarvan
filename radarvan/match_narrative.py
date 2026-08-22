"""Retell one match as an ordered list of sentences, from data already parsed.

Every beat is a fact the match details already carry - who drew first blood,
who reached rank 5 first, who launched a superweapon, who ran out of dozers -
rendered as a sentence and sorted onto a timeline. There is no model call and
no new derivation: this is a projection of ``MatchDetails``, the same way
``routes/matches.get_build_orders`` is, so it shares the durable details cache
and adds nothing to ``DETAILS_VERSION``.

The editorial work is the *selection*. A four-versus-four game has eight
players' worth of rank-ups, upgrades and powers - dumping all of them is a
log, not a story - so the per-player milestones are narrowed to the first
player to reach each one, superweapon launches are kept in full because they
decide games, and the closing summary beats name only the leader of each
ledger.
"""

from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from .api_types import (
    General,
    KillEventOutput,
    MatchDetails,
    MatchInfo,
    MatchNarrative,
    NarrativeBeat,
)
from .game_composition import RosterSlot
from .player_ids import resolve_player_name
from .replay_files import map_basename
from .replay_helpers import clean_object_name

# A superweapon launch is decisive enough to always be worth a line, but a
# 40-minute game with three nuke silos would otherwise be nothing else.
MAX_SUPERWEAPON_BEATS = 6

# Only call out a single kill when it's actually a moment - anything cheaper
# than a tech structure is just a skirmish trade.
BIG_KILL_MIN_VALUE = 1500


def _canonical_names(match: MatchInfo) -> dict[str, str]:
    """Raw in-game name -> canonical player name for this match's competitors.

    Every ``MatchDetails`` field is keyed by the raw replay name, so this is
    the bridge to the names the rest of the app shows. Colour disambiguates
    the shared "pc" alias (see CLAUDE.md).
    """
    return {
        slot.name: resolve_player_name(slot.name, slot.color)
        for slot in match.roster().competitors
        if slot.name
    }


def _name(canonical: dict[str, str], raw: str) -> str:
    return canonical.get(raw, raw)


class Side(NamedTuple):
    """One side of the match and whether it won."""

    slots: list[RosterSlot]
    won: bool


def _sides(match: MatchInfo) -> list[Side]:
    """The match's sides, in a stable order, each flagged with whether it won.

    Teams when there are teams. An FFA has none - every competitor sits on team
    0, so ``participants`` is empty there - and each player is their own side,
    with the result read off their own ``won`` flag rather than
    ``winning_team`` (which is NONE for a free-for-all).
    """
    grouped: dict[int, list[RosterSlot]] = defaultdict(list)
    for slot in match.roster().participants:
        grouped[slot.team].append(slot)
    if grouped:
        return [
            Side(slots=slots, won=team == match.winning_team)
            for team, slots in sorted(grouped.items())
        ]
    return [Side(slots=[slot], won=slot.won) for slot in match.roster().competitors]


def _display_map(match: MatchInfo) -> str:
    """The map as the rest of the app shows it - stored as a path, read as a name."""
    return map_basename(match.map).removesuffix(".map")


def _join(names: list[str]) -> str:
    """ "a", "a & b", "a, b & c"."""
    if not names:
        return "nobody"
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} & {names[-1]}"


def _side(slots: list[RosterSlot], canonical: dict[str, str]) -> str:
    return _join([_name(canonical, s.name) for s in slots])


def _with_generals(slots: list[RosterSlot], canonical: dict[str, str]) -> str:
    return _join(
        [f"{_name(canonical, s.name)} ({General(s.general).name})" for s in slots]
    )


def _headline(match: MatchInfo, canonical: dict[str, str]) -> str:
    """One line naming the result, the map and the length."""
    sides = _sides(match)
    length = f"{match.duration_minutes:.0f} min"
    won = [side for side in sides if side.won]
    lost = [side for side in sides if not side.won]
    if not won or not lost:
        listed = " vs ".join(_side(side.slots, canonical) for side in sides)
        state = match.incomplete or "no result recorded"
        return f"{listed} on {_display_map(match)} - {length}, {state}"
    winners = _join([_side(side.slots, canonical) for side in won])
    losers = _join([_side(side.slots, canonical) for side in lost])
    return f"{winners} beat {losers} on {_display_map(match)} in {length}"


def _setup_beat(match: MatchInfo, canonical: dict[str, str]) -> NarrativeBeat:
    lineup = " vs ".join(
        _with_generals(side.slots, canonical) for side in _sides(match)
    )
    category = match.composition.category if match.composition else "game"
    return NarrativeBeat(
        kind="setup",
        text=f"{category} on {_display_map(match)}. {lineup}.",
    )


def _first_blood_beats(
    details: MatchDetails, canonical: dict[str, str]
) -> list[NarrativeBeat]:
    beats = []
    if details.first_blood is not None:
        event = details.first_blood
        beats.append(
            NarrativeBeat(
                kind="first_blood",
                at_minute=event.atMinute,
                player_name=_name(canonical, event.attacker),
                text=(
                    f"{_name(canonical, event.attacker)} drew first blood on "
                    f"{_name(canonical, event.victim)}."
                ),
            )
        )
    if details.building_first_blood is not None:
        event = details.building_first_blood
        beats.append(
            NarrativeBeat(
                kind="first_blood",
                at_minute=event.atMinute,
                player_name=_name(canonical, event.attacker),
                text=(
                    f"{_name(canonical, event.attacker)} took down the first "
                    f"building, {_name(canonical, event.victim)}'s."
                ),
            )
        )
    return beats


def _earliest(times: dict[str, float]) -> tuple[str, float] | None:
    """The (player, minute) that got there first, or None if nobody did."""
    if not times:
        return None
    raw = min(times, key=lambda key: times[key])
    return raw, times[raw]


def _milestone_beats(
    details: MatchDetails, canonical: dict[str, str]
) -> list[NarrativeBeat]:
    """First-to-reach beats for the milestones a game is often decided by.

    Only the first player is named: in an 8-player game every one of these is
    otherwise eight nearly identical lines.
    """
    beats = []
    rank_5 = _earliest(details.time_to_rank_5)
    if rank_5 is not None:
        raw, minute = rank_5
        beats.append(
            NarrativeBeat(
                kind="milestone",
                at_minute=minute,
                player_name=_name(canonical, raw),
                text=f"{_name(canonical, raw)} was first to generals rank 5.",
            )
        )
    search_destroy = _earliest(details.time_to_search_destroy)
    if search_destroy is not None:
        raw, minute = search_destroy
        beats.append(
            NarrativeBeat(
                kind="milestone",
                at_minute=minute,
                player_name=_name(canonical, raw),
                text=f"{_name(canonical, raw)} flipped to Search & Destroy.",
            )
        )
    return beats


def _collapse_beats(
    details: MatchDetails, canonical: dict[str, str]
) -> list[NarrativeBeat]:
    """Every player who went "hunted" - no dozer left and no way to build one.

    Not narrowed to the first: this is the moment a player is mathematically
    finished, and in a team game which of them it happened to is the story.
    """
    return [
        NarrativeBeat(
            kind="collapse",
            at_minute=minute,
            player_name=_name(canonical, raw),
            text=f"{_name(canonical, raw)} went hunted - no dozers, no way back.",
        )
        for raw, minute in sorted(details.time_to_hunted.items(), key=lambda kv: kv[1])
    ]


class _Launches(NamedTuple):
    """When a (player, weapon) pair first fired, and how often it did.

    ``times`` rather than ``count``: a NamedTuple field named ``count``
    shadows ``tuple.count`` and the annotation is rejected.
    """

    first_minute: float
    times: int


def _superweapon_beats(
    details: MatchDetails, canonical: dict[str, str]
) -> list[NarrativeBeat]:
    """One beat per (player, weapon), not per launch.

    ``superweapon_activated`` also carries repeatable generals powers - a
    Spectre Gunship fired six times is one recurring habit, and rendered a
    launch at a time it crowds every other beat out of the timeline.
    """
    grouped: dict[tuple[str, str], _Launches] = {}
    for event in details.timeline_events:
        if event.event_type != "superweapon_activated":
            continue
        key = (event.player_name, event.event_name)
        seen = grouped.get(key)
        grouped[key] = _Launches(
            first_minute=(
                event.at_minute
                if seen is None
                else min(seen.first_minute, event.at_minute)
            ),
            times=1 if seen is None else seen.times + 1,
        )
    ordered = sorted(grouped.items(), key=lambda item: item[1].first_minute)
    beats = []
    for (raw, weapon), launches in ordered[:MAX_SUPERWEAPON_BEATS]:
        repeat = f" (x{launches.times})" if launches.times > 1 else ""
        beats.append(
            NarrativeBeat(
                kind="superweapon",
                at_minute=launches.first_minute,
                player_name=_name(canonical, raw),
                text=f"{_name(canonical, raw)} fired {weapon}{repeat}.",
            )
        )
    return beats


def _biggest_kill_beat(
    details: MatchDetails, canonical: dict[str, str]
) -> NarrativeBeat | None:
    """The single most expensive thing destroyed all game, if it was worth it."""

    def value(event: KillEventOutput) -> int:
        return event.value

    kills = [
        event for event in details.kill_events if event.value >= BIG_KILL_MIN_VALUE
    ]
    if not kills:
        return None
    best = max(kills, key=value)
    killer = clean_object_name(best.killer) or best.killer
    victim = clean_object_name(best.victim) or best.victim
    return NarrativeBeat(
        kind="damage",
        at_minute=best.at_minute,
        player_name=_name(canonical, best.killer_player),
        text=(
            f"Priciest kill of the game: {_name(canonical, best.killer_player)}'s "
            f"{killer} killed {_name(canonical, best.victim_player)}'s {victim} "
            f"(${best.value:,})."
        ),
    )


def _leader(totals: dict[str, int | float]) -> tuple[str, float] | None:
    if not totals:
        return None
    raw = max(totals, key=lambda key: totals[key])
    if totals[raw] <= 0:
        return None
    return raw, float(totals[raw])


def _ledger_beats(
    details: MatchDetails, canonical: dict[str, str]
) -> list[NarrativeBeat]:
    """Closing, untimed beats: who earned most, who destroyed most, who clicked most."""
    beats = []
    earned = _leader({**details.player_money_collected})
    if earned is not None:
        raw, amount = earned
        beats.append(
            NarrativeBeat(
                kind="economy",
                player_name=_name(canonical, raw),
                text=f"{_name(canonical, raw)} banked the most, ${amount:,.0f}.",
            )
        )
    destroyed: dict[str, int | float] = defaultdict(int)
    for event in details.kill_events:
        destroyed[event.killer_player] += event.value
    top_damage = _leader(dict(destroyed))
    if top_damage is not None:
        raw, amount = top_damage
        beats.append(
            NarrativeBeat(
                kind="damage",
                player_name=_name(canonical, raw),
                text=(
                    f"{_name(canonical, raw)} did the most damage, "
                    f"${amount:,.0f} destroyed."
                ),
            )
        )
    apms = {entry.player_name: entry.apm for entry in details.apms}
    fastest = _leader(dict(apms))
    if fastest is not None:
        raw, rate = fastest
        beats.append(
            NarrativeBeat(
                kind="tempo",
                player_name=_name(canonical, raw),
                text=f"{_name(canonical, raw)} had the fastest hands at {rate:.0f} APM.",
            )
        )
    return beats


def _result_beat(match: MatchInfo, canonical: dict[str, str]) -> NarrativeBeat:
    won = [side for side in _sides(match) if side.won]
    if not won:
        return NarrativeBeat(
            kind="result",
            text=(
                f"No result recorded after {match.duration_minutes:.1f} minutes"
                + (f" ({match.incomplete})." if match.incomplete else ".")
            ),
        )
    winners = _join([_side(side.slots, canonical) for side in won])
    return NarrativeBeat(
        kind="result",
        text=f"{winners} took it at {match.duration_minutes:.1f} minutes.",
    )


def build_narrative(match: MatchInfo, details: MatchDetails | None) -> MatchNarrative:
    """The match as an ordered story: setup, then the timeline, then the ledger.

    ``details`` is None for a match whose replay hasn't been parsed - the
    headline still comes from the match row, so the caller always has
    something to render.
    """
    canonical = _canonical_names(match)
    headline = _headline(match, canonical)
    if details is None:
        return MatchNarrative(match_id=match.id, headline=headline, beats=[])

    timed = [
        *_first_blood_beats(details, canonical),
        *_milestone_beats(details, canonical),
        *_superweapon_beats(details, canonical),
        *_collapse_beats(details, canonical),
    ]
    big_kill = _biggest_kill_beat(details, canonical)
    if big_kill is not None:
        timed.append(big_kill)
    # `at_minute` is set on every beat in `timed` by construction; the `or 0.0`
    # is for the type checker rather than a real case.
    timed.sort(key=lambda beat: beat.at_minute or 0.0)

    beats = [
        _setup_beat(match, canonical),
        *timed,
        *_ledger_beats(details, canonical),
        _result_beat(match, canonical),
    ]
    return MatchNarrative(match_id=match.id, headline=headline, beats=beats)
