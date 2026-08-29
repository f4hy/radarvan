"""Purpose-built, pre-trimmed per-game data for the LLM-generated post-game
set recap.

The pre-game blurb (``hype_data``) works from lifetime aggregates; the recap
works from what actually happened in the games of one best-of-N set, so this
module reduces each game's ``MatchDetails`` - which carries per-minute APM
series, every kill event, every map event - down to the handful of facts a
recap can actually retell: who won on what, the tempo (duration, first
blood, rank progression), the economy (money earned/spent), the damage
ledger (value destroyed/lost, which units did the killing), and the opening
build.

Same conventions as ``hype_data``: rendered as plain labeled text rather
than JSON (nothing downstream re-parses it), generals and object names in
human form, and player names alias-resolved to their canonical bracket
names - the replay carries in-game aliases (``Grn``, ``131``), and a recap
that calls a player by their alias reads as a different person.

Per-game blocks are deliberately *not* filtered down to "interesting"
stats the way ``hype_data`` filters percentiles: which numbers make the
story is exactly what the model is being asked to work out, and a set is at
most nine games, so the whole ledger fits comfortably.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from ..api_types import (
    BracketMatchOutput,
    BuildOrderEntry,
    FirstBlood,
    MatchDetails,
    MatchInfo,
    PlayerSummary,
)
from ..player_ids import resolve_player_name
from ..replay_helpers import clean_object_name
from ..generals_powers import clean_power_name
from . import hype_data


# How much of each per-player list survives into the prompt. The opening is
# where a game's plan is visible, and the tail of a 200-unit production
# queue says nothing a recap could use.
MAX_OPENING_BUILDINGS = 10
MAX_OPENING_UNITS = 10
MAX_TOP_KILLERS = 5
MAX_POWERS = 8

# cncstats emits unnamed upgrades as the literal string "dummy" for some
# replays (whole upgrade lists can be nothing but these). They carry no
# information and would otherwise read to the model as a real upgrade name.
_PLACEHOLDER_NAMES = {"dummy", ""}


class SummaryKiller(BaseModel):
    """One unit type and what it destroyed, from this player's kill events."""

    name: str
    kills: int
    value: int


class SummaryPlayerGame(BaseModel):
    """One player's ledger for one game."""

    player: str
    general: str
    won: bool
    apm: float | None
    money_collected: int
    money_spent: int
    value_destroyed: int
    value_lost: int
    units_destroyed: int
    buildings_destroyed: int
    units_lost: int
    buildings_lost: int
    highest_rank: int | None
    rank_5_minute: float | None
    search_destroy_minute: float | None
    # Minute this player went "hunted" - no dozer/worker left and no way to
    # build one. Usually None simply because it usually doesn't happen: a
    # recap only ever covers a just-played set, and those replays are parsed
    # at cncstats statsVersion 3, which always carries the stream. (Replays
    # parsed before that have no stream at all, so a *historical* match can
    # read as None for the other reason - but nothing here looks at those.)
    # Rare enough, and decisive enough, to get its own rendered line rather
    # than joining the milestone list - see `_render_player_game`.
    hunted_minute: float | None
    opening_buildings: list[str]
    opening_units: list[str]
    upgrades: list[str]
    powers_used: list[str]
    superweapons_built: list[str]
    superweapons_fired: list[str]
    tech_captures: list[str]
    low_power_minutes: list[float]
    top_killers: list[SummaryKiller]


class SummaryGame(BaseModel):
    """One game of the set: the result line plus both players' ledgers.

    ``outcome`` is the same ``HypeTournamentGame`` the pre-game blurb builds,
    so map/generals/mirror-detection stay one implementation. ``players`` is
    empty when the match's details couldn't be loaded (an unparsed or
    S3-missing replay) - the result line is still worth having, so the game
    isn't dropped.
    """

    match_id: int
    outcome: hype_data.HypeTournamentGame
    # "Alice killed Bob's first unit at 1.5min", already alias-resolved.
    first_blood: str | None
    first_building_killed: str | None
    players: list[SummaryPlayerGame]


class SummarySet(BaseModel):
    """A completed best-of-N bracket match and every game inside it."""

    stage: str
    round_name: str
    best_of: int | None
    player_a: str
    player_b: str
    score_a: int | None
    score_b: int | None
    winner: str
    loser: str
    games: list[SummaryGame]
    reverse_pairs: list[hype_data.HypeReversePair]


def _canonical_names(match: MatchInfo) -> dict[str, str]:
    """Raw in-game name -> canonical player name, for this match's competitors.

    Every ``MatchDetails`` field is keyed by the raw replay name, so this is
    the bridge to the bracket's names. Colors come from the roster because
    "pc" is a shared alias (see CLAUDE.md).
    """
    return {
        slot.name: resolve_player_name(slot.name, slot.color)
        for slot in match.roster().competitors
        if slot.name
    }


def _render_first_blood(
    event: FirstBlood | None, canonical: dict[str, str], what: str
) -> str | None:
    if event is None:
        return None
    attacker = canonical.get(event.attacker, event.attacker)
    victim = canonical.get(event.victim, event.victim)
    return f"{attacker} took {what} off {victim} at {event.atMinute:.1f}min"


def _rank_from_event_name(event_name: str) -> int | None:
    """ "Rank 3" -> 3. Returns None for anything that doesn't parse."""
    _, _, tail = event_name.partition("Rank ")
    return int(tail) if tail.isdigit() else None


def _top_killers(details: MatchDetails, raw_name: str) -> list[SummaryKiller]:
    """This player's most destructive unit types, by value destroyed.

    Kill events name the *unit that got the kill*, which is the one place the
    data says how a game was actually won ("his Comanches did 12k of it") -
    the per-player totals in the player summary can't.
    """
    kills: Counter[str] = Counter()
    value: Counter[str] = Counter()
    for event in details.kill_events:
        if event.killer_player != raw_name:
            continue
        name = clean_object_name(event.killer) or event.killer
        kills[name] += 1
        value[name] += event.value
    return [
        SummaryKiller(name=name, kills=kills[name], value=total)
        for name, total in value.most_common(MAX_TOP_KILLERS)
    ]


def _build_player_game(
    canonical: str,
    raw_name: str,
    general: str,
    won: bool,
    details: MatchDetails,
    summary: PlayerSummary | None,
) -> SummaryPlayerGame:
    apm = next(
        (a.apm for a in details.apms if a.player_name == raw_name),
        None,
    )
    build_order = details.build_orders.get(raw_name)
    events = [e for e in details.timeline_events if e.player_name == raw_name]
    ranks = [
        rank
        for rank in (
            _rank_from_event_name(e.event_name)
            for e in events
            if e.event_type == "rank_up"
        )
        if rank is not None
    ]

    def _entries(entries: list[BuildOrderEntry], limit: int) -> list[str]:
        rows: list[str] = []
        for entry in entries:
            if entry.name.lower() in _PLACEHOLDER_NAMES:
                continue
            count = f" x{entry.count}" if entry.count > 1 else ""
            rows.append(f"{entry.name}{count} @ {entry.at_minute:.1f}min")
            if len(rows) >= limit:
                break
        return rows

    destroyed = summary.UnitsDestroyed if summary else {}
    buildings_destroyed = summary.BuildingsDestroyed if summary else {}
    lost = summary.UnitsLost if summary else {}
    buildings_lost = summary.BuildingsLost if summary else {}
    top_killers = _top_killers(details, raw_name)

    return SummaryPlayerGame(
        player=canonical,
        general=general,
        won=won,
        apm=apm,
        money_collected=details.player_money_collected.get(raw_name, 0),
        money_spent=details.player_money_spent.get(raw_name, 0),
        value_destroyed=(
            sum(v.TotalSpent for v in destroyed.values())
            + sum(v.TotalSpent for v in buildings_destroyed.values())
        ),
        value_lost=(
            sum(v.TotalSpent for v in lost.values())
            + sum(v.TotalSpent for v in buildings_lost.values())
        ),
        units_destroyed=sum(v.Count for v in destroyed.values()),
        buildings_destroyed=sum(v.Count for v in buildings_destroyed.values()),
        units_lost=sum(v.Count for v in lost.values()),
        buildings_lost=sum(v.Count for v in buildings_lost.values()),
        highest_rank=max(ranks) if ranks else None,
        rank_5_minute=details.time_to_rank_5.get(raw_name),
        search_destroy_minute=details.time_to_search_destroy.get(raw_name),
        hunted_minute=details.time_to_hunted.get(raw_name),
        opening_buildings=_entries(
            build_order.buildings if build_order else [], MAX_OPENING_BUILDINGS
        ),
        opening_units=_entries(
            build_order.units if build_order else [], MAX_OPENING_UNITS
        ),
        upgrades=_entries(build_order.upgrades if build_order else [], MAX_POWERS),
        powers_used=[
            f"{clean_power_name(name) or name} x{count}"
            for name, count in sorted(
                (summary.PowersUsed if summary else {}).items(),
                key=lambda kv: -kv[1],
            )[:MAX_POWERS]
        ],
        superweapons_built=[
            f"{e.event_name} @ {e.at_minute:.1f}min"
            for e in events
            if e.event_type == "superweapon_built"
        ],
        superweapons_fired=[
            f"{e.event_name} @ {e.at_minute:.1f}min"
            for e in events
            if e.event_type == "superweapon_activated"
        ],
        tech_captures=[
            f"{e.event_name} @ {e.at_minute:.1f}min"
            for e in events
            if e.event_type == "tech_capture"
        ],
        low_power_minutes=[e.at_minute for e in events if e.event_type == "low_power"],
        top_killers=top_killers,
    )


def build_summary_game(
    match: MatchInfo, details: MatchDetails | None
) -> SummaryGame | None:
    """One linked replay as a recap-ready game, or None if it isn't a clean
    two-human decided 1v1 (see ``hype_data.tournament_game``)."""
    outcome = hype_data.tournament_game(match)
    if outcome is None:
        return None
    canonical = _canonical_names(match)
    if details is None:
        return SummaryGame(
            match_id=match.id,
            outcome=outcome,
            first_blood=None,
            first_building_killed=None,
            players=[],
        )

    summaries = {s.Name: s for s in details.player_summary}
    generals = {
        canonical[slot.name]: slot
        for slot in match.roster().human_participants
        if slot.name in canonical
    }
    players = []
    # Winner first: every rendered block reads as "the winner did X, the
    # loser did Y", which is the order a recap retells it in.
    for name in (outcome.winner, outcome.loser):
        slot = generals.get(name)
        if slot is None:
            continue
        players.append(
            _build_player_game(
                canonical=name,
                raw_name=slot.name,
                general=(
                    outcome.winner_general
                    if name == outcome.winner
                    else outcome.loser_general
                ),
                won=name == outcome.winner,
                details=details,
                summary=summaries.get(slot.name),
            )
        )
    return SummaryGame(
        match_id=match.id,
        outcome=outcome,
        first_blood=_render_first_blood(details.first_blood, canonical, "first blood"),
        first_building_killed=_render_first_blood(
            details.building_first_blood, canonical, "the first building"
        ),
        players=players,
    )


def build_summary_set(
    bracket_match: BracketMatchOutput,
    games: list[SummaryGame],
) -> SummarySet:
    """Assemble the whole set from its bracket row and its built games.

    Callers must only pass a completed match with both players known - the
    route enforces that before spending an LLM call (see routes/commentary).
    """
    winner = bracket_match.winner
    if (
        winner is None
        or bracket_match.player_a is None
        or bracket_match.player_b is None
    ):
        raise ValueError(
            f"{bracket_match.match_id} is not a completed set with both players known"
        )
    loser = (
        bracket_match.player_b
        if winner == bracket_match.player_a
        else bracket_match.player_a
    )
    return SummarySet(
        stage=bracket_match.match_id,
        round_name=bracket_match.round_name,
        best_of=bracket_match.best_of,
        player_a=bracket_match.player_a,
        player_b=bracket_match.player_b,
        score_a=bracket_match.score_a,
        score_b=bracket_match.score_b,
        winner=winner,
        loser=loser,
        games=games,
        reverse_pairs=hype_data.reverse_pairs([g.outcome for g in games]),
    )


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _render_player_game(player: SummaryPlayerGame) -> list[str]:
    result = "WON" if player.won else "lost"
    lines = [f"  {player.player} ({player.general}) - {result}"]

    economy = [
        f"earned ${player.money_collected:,}",
        f"spent ${player.money_spent:,}",
    ]
    if player.apm is not None:
        economy.append(f"{player.apm:.0f} APM")
    lines.append(f"    Economy/tempo: {', '.join(economy)}")

    lines.append(
        f"    Damage ledger: destroyed ${player.value_destroyed:,} worth "
        f"({_plural(player.units_destroyed, 'unit')}, "
        f"{_plural(player.buildings_destroyed, 'building')}); "
        f"lost ${player.value_lost:,} worth "
        f"({_plural(player.units_lost, 'unit')}, "
        f"{_plural(player.buildings_lost, 'building')})"
    )

    progression = []
    if player.highest_rank is not None:
        progression.append(f"reached rank {player.highest_rank}")
    if player.rank_5_minute is not None:
        progression.append(f"rank 5 at {player.rank_5_minute:.1f}min")
    if player.search_destroy_minute is not None:
        progression.append(f"Search & Destroy at {player.search_destroy_minute:.1f}min")
    if player.low_power_minutes:
        progression.append(
            "went low on power at "
            + ", ".join(f"{m:.1f}min" for m in player.low_power_minutes)
        )
    if progression:
        lines.append(f"    Progression: {'; '.join(progression)}")

    # Deliberately its own line rather than another entry in `progression`:
    # going hunted is not a milestone on the way to something, it is the point
    # where this player stopped being able to rebuild. Spelled out in full
    # because "hunted" is engine jargon the model has no reason to know.
    if player.hunted_minute is not None:
        lines.append(
            f"    Hunted: production-locked at {player.hunted_minute:.1f}min - "
            "no dozer or worker left and no way to build one, so nothing "
            "lost after this point could be replaced"
        )

    if player.opening_buildings:
        lines.append(f"    Opening buildings: {', '.join(player.opening_buildings)}")
    if player.opening_units:
        lines.append(f"    First units: {', '.join(player.opening_units)}")
    if player.upgrades:
        lines.append(f"    Upgrades: {', '.join(player.upgrades)}")
    if player.powers_used:
        lines.append(f"    Powers/abilities used: {', '.join(player.powers_used)}")
    if player.tech_captures:
        lines.append(f"    Tech captured: {', '.join(player.tech_captures)}")
    if player.superweapons_built:
        lines.append(f"    Superweapons built: {', '.join(player.superweapons_built)}")
    if player.superweapons_fired:
        lines.append(f"    Superweapons fired: {', '.join(player.superweapons_fired)}")
    if player.top_killers:
        lines.append(
            "    Top killers: "
            + ", ".join(
                f"{k.name} ({_plural(k.kills, 'kill')}, ${k.value:,})"
                for k in player.top_killers
            )
        )
    return lines


def _render_game(index: int, game: SummaryGame) -> list[str]:
    outcome = game.outcome
    mirror = " [MIRROR - both on the same general]" if outcome.is_mirror else ""
    lines = [
        f"Game {index} on {outcome.map} ({outcome.duration_minutes:.1f} min){mirror}",
        f"  Result: {outcome.winner} ({outcome.winner_general}) beat "
        f"{outcome.loser} ({outcome.loser_general})",
    ]
    if game.first_blood:
        lines.append(f"  First blood: {game.first_blood}")
    if game.first_building_killed:
        lines.append(f"  First building down: {game.first_building_killed}")
    for player in game.players:
        lines.extend(_render_player_game(player))
    if not game.players:
        lines.append("  (no detailed stats available for this game)")
    return lines


def render_summary_set(summary: SummarySet) -> str:
    """Plain labeled text for the whole set - see the module docstring for
    why this isn't JSON."""
    if summary.score_a is None or summary.score_b is None:
        score = ""
    elif summary.winner == summary.player_a:
        score = f" {summary.score_a}-{summary.score_b}"
    else:
        score = f" {summary.score_b}-{summary.score_a}"
    best_of = f" (best of {summary.best_of})" if summary.best_of else ""

    lines = [
        f"{summary.round_name}{best_of}: {summary.winner} beat {summary.loser}{score}",
        "",
    ]
    for index, game in enumerate(summary.games, start=1):
        lines.extend(_render_game(index, game))
        lines.append("")

    if summary.reverse_pairs:
        lines.append(
            "Reversed pairs (the same draw played both ways - the only place a "
            "result belongs to the player rather than the draw):"
        )
        for pair in summary.reverse_pairs:
            verdict = (
                f"{pair.swept_by} won both sides"
                if pair.swept_by
                else "split 1-1, each winning their turn on it"
            )
            lines.append(
                f"- {pair.map} ({pair.general_a} vs {pair.general_b}): {verdict}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()


def missing_games_note(summary: SummarySet) -> str:
    """A warning line when the set's replays are only partly linked, else "".

    Without it the model would count the games it was given and describe a
    5-game set as a sweep.
    """
    played = (summary.score_a or 0) + (summary.score_b or 0)
    if played and len(summary.games) < played:
        return (
            f"NOTE: only {len(summary.games)} of the {played} games in this set "
            "have replays on record - do not claim the set was shorter than it was."
        )
    return ""
