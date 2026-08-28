"""The once-a-night, LLM-written game-night recap.

The third generator in this package, and the cheapest to feed: where the
bracket recap reduces raw ``MatchDetails`` itself (``summary_data``), this one
is handed work already done - the deterministic recap from ``game_night`` and
one ``MatchNarrative`` per game from ``match_narrative``. Both of those exist
because the page shows them, so the prompt is a rendering of what a reader
already sees rather than a second, parallel reduction of the same replays that
could drift from it.

What this module owns on top of that is the *clock*. Every game is rendered
with the window it occupied rather than the moment it started, and the gaps
between games are subtracted here and rendered as breaks. Both exist because
the model was asked to do that arithmetic and got it wrong in the obvious way:
handed start times only, and a game list with the uncounted games filtered out
of it, it reported a 39-minute hole - the last 3v3 ending at 11:02pm, the first
1v1 starting at 11:41pm - as a "40-minute breather". The hole was a 29-minute
free-for-all. See ``queries.game_night.night_narratives`` for the other half.

**This module is only ever called by the nightly scheduler job.** Nothing on
the read path generates: ``routes/game_night`` returns whatever the job wrote
and null otherwise. That is deliberate - the other two generators are keyed on
bounded, enumerable things (a matchup, a bracket stage) and can safely fill
their cache on a miss, but a date is unbounded, and a page that generated on
demand would bill a call for every night anyone happened to scroll back to.

Like the other generators, this one always regenerates when called; the
"already have one for this night" check lives at the call site
(``schedule.compute_game_night_summary``).

Unlike the other two, though, the *write* lives here rather than at the
route layer. Storing is not a cache for this feature, it is the delivery
mechanism - nothing else ever produces the text - and there are two callers
(the nightly job and the ops endpoint). Duplicating "generate, then persist
with the right provider and match count" across both is how a night gets
billed twice or stored describing a different number of games than it was
written from.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import structlog

from ..api_types import GameNightRecap, MatchNarrative
from ..queries.game_night import NightGame
from ..repositories import GameNightSummaryRepo
from ..utils import GAME_NIGHT_TZ
from . import llm
from .night_prompts import NIGHT_GUIDELINES

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = NIGHT_GUIDELINES

# Serializes generation process-wide. The nightly job and a hand-triggered
# ops run are separate callers of the same billed operation, and two of them
# in flight for one night would pay twice to write one row. Held here rather
# than at either call site so neither can forget it.
generation_lock = asyncio.Lock()

# A single game is a match, not a game night. Below this the deterministic
# recap already says everything there is to say, and spending a real LLM call
# on it isn't worth it - most one-match "nights" are a stray upload. Lives
# here rather than at either call site for the reason in the module docstring:
# the nightly job and the ops backfill must refuse the same nights.
MIN_MATCHES_FOR_SUMMARY = 2

# A night is normally under fifteen games. The cap is for the pathological
# case - a marathon, or a backlog of uploads all landing on one night key -
# where the beat list would otherwise dominate the prompt without telling the
# model anything the standings don't already.
MAX_GAMES_RENDERED = 20

# How long a gap between two games has to be before it is a break somebody
# would mention rather than the ordinary business of picking teams and
# loading a map. Inter-game gaps in this group run 1-6 minutes.
#
# The break is *rendered*, not left to the model to work out, for the reason
# this whole seam exists: gap arithmetic across a list of games is exactly the
# kind of thing an LLM does confidently and wrongly, and it is one subtraction
# to do here. The model is told the breaks it is given are the only ones.
MIN_BREAK_MINUTES = 20.0


def _local(when: datetime) -> str:
    """Wall-clock time as the group experienced it.

    Everything is stored UTC, but a game night *is* a US Eastern evening (the
    date key rolls over at 5am there), so UTC times would put the whole night
    on the wrong side of midnight and read as nonsense to the model.
    """
    return f"{when.astimezone(GAME_NIGHT_TZ):%-I:%M%p}".replace("AM", "am").replace(
        "PM", "pm"
    )


def _render_clock(recap: GameNightRecap) -> str | None:
    if recap.started_at is None or recap.ended_at is None:
        return None
    span = recap.ended_at - recap.started_at
    hours = span.total_seconds() / 3600
    return (
        f"first game {_local(recap.started_at)}, last game ended "
        f"{_local(recap.ended_at)} ({hours:.1f}h wall clock, "
        f"{recap.total_minutes:.0f} min of it actually in game)"
    )


def _render_standings(recap: GameNightRecap) -> list[str]:
    lines = []
    for line in recap.players:
        parts = [f"  {line.player}: {line.wins}-{line.losses}"]
        if line.best_streak > 1:
            parts.append(f"best streak {line.best_streak}")
        if line.best_apm is not None:
            parts.append(f"top APM {line.best_apm:.0f}")
        if line.generals:
            parts.append(f"dealt {', '.join(line.generals)}")
        lines.append(" - ".join(parts))
    return lines


def _ended_at(narrative: MatchNarrative) -> datetime | None:
    if narrative.started_at is None:
        return None
    return narrative.started_at + timedelta(minutes=narrative.duration_minutes)


def _render_span(narrative: MatchNarrative) -> str:
    """ "9:38pm-9:48pm - ", the window the game actually occupied.

    A start time alone is what produced the "40-minute breather" that was a
    29-minute game: the reader has to subtract the previous game's length out
    of a start-to-start gap, and there is no reason to make them.
    """
    ended = _ended_at(narrative)
    if narrative.started_at is None or ended is None:
        return ""
    return f"{_local(narrative.started_at)}-{_local(ended)} - "


def _render_break(previous: MatchNarrative, current: MatchNarrative) -> str | None:
    """ "-- 38 min break --" between two games, when there really was one."""
    ended = _ended_at(previous)
    if ended is None or current.started_at is None:
        return None
    minutes = (current.started_at - ended).total_seconds() / 60
    if minutes < MIN_BREAK_MINUTES:
        return None
    return f"-- {minutes:.0f} min break --"


def _render_narrative(game: NightGame) -> list[str]:
    narrative = game.narrative
    span = _render_span(narrative)
    label = f"[TOURNAMENT: {narrative.tournament}] " if narrative.tournament else ""
    if game.uncounted is not None:
        # Ahead of the tournament tag because it is the stronger caveat: this
        # game happened and its beats are real, but its result is in none of
        # the numbers above.
        label = f"[NOT IN THE STANDINGS - {game.uncounted}] {label}"
    lines = [f"  {span}{label}{narrative.headline}"]
    for beat in narrative.beats:
        # The setup beat restates the lineup the headline already carries, and
        # the result beat restates the result - both are noise once the
        # headline is there.
        if beat.kind in {"setup", "result"}:
            continue
        stamp = f"{beat.at_minute:.1f}min - " if beat.at_minute is not None else ""
        lines.append(f"    {stamp}{beat.text}")
    return lines


def render_night(recap: GameNightRecap, games: list[NightGame]) -> str:
    """The night as plain labelled text - the same convention as ``summary_data``.

    Rendered rather than serialized as JSON because nothing downstream
    re-parses it, and prose-shaped input is what the model is being asked to
    write from.
    """
    sections: list[str] = []

    shape = [f"Games played: {recap.match_count}"]
    if recap.counted_matches != recap.match_count:
        shape.append(
            f"Of those, {recap.counted_matches} were decided competitive games. "
            "The rest were still played and are still below in GAME BY GAME, "
            "marked [NOT IN THE STANDINGS] with the reason - their results are "
            "in none of the numbers above."
        )
    if recap.formats:
        shape.append(
            "Formats: "
            + ", ".join(f"{count}x {fmt}" for fmt, count in recap.formats.items())
        )
    if recap.maps:
        shape.append(
            "Maps: "
            + ", ".join(f"{name} ({count})" for name, count in recap.maps.items())
        )
    clock = _render_clock(recap)
    if clock is not None:
        shape.append(f"Clock: {clock}")
    if recap.median_minutes is not None:
        shape.append(f"Median game length: {recap.median_minutes:.1f} min")
    sections.append("THE NIGHT\n" + "\n".join(shape))

    if recap.players:
        sections.append("STANDINGS\n" + "\n".join(_render_standings(recap)))

    if recap.highlights:
        sections.append(
            "HIGHLIGHTS\n"
            + "\n".join(f"  {item.title}: {item.detail}" for item in recap.highlights)
        )

    if games:
        blocks: list[str] = []
        previous: MatchNarrative | None = None
        for index, game in enumerate(games[:MAX_GAMES_RENDERED], start=1):
            if previous is not None:
                gap = _render_break(previous, game.narrative)
                if gap is not None:
                    blocks.append(gap)
            blocks.append(f"Game {index}:\n" + "\n".join(_render_narrative(game)))
            previous = game.narrative
        sections.append("GAME BY GAME\n" + "\n\n".join(blocks))

    return "\n\n".join(sections)


def build_user_message(recap: GameNightRecap, games: list[NightGame]) -> str:
    """Assemble the user turn. Separate from ``build_prompt`` so it is
    unit-testable without a DB or a network call."""
    return (
        f"Write the game-night recap for {recap.date:%A %-d %B %Y}.\n\n"
        "<game_night>\n"
        f"{render_night(recap, games)}\n"
        "</game_night>"
    )


def build_prompt(recap: GameNightRecap, games: list[NightGame]) -> llm.Prompt:
    """The exact system + user content that would be sent to the active
    provider for this night - without calling the API."""
    return llm.Prompt(
        system=SYSTEM_PROMPT, user_message=build_user_message(recap, games)
    )


def generate_summary(recap: GameNightRecap, games: list[NightGame]) -> str:
    """Generate the recap for one game night, using whichever provider
    COMMENTARY_PROVIDER selects. Always spends a real call - see the module
    docstring for who is allowed to call this."""
    prompt = build_prompt(recap, games)
    return llm.generate(
        prompt,
        kind="Game night recap",
        label=f"{recap.date} ({recap.match_count} games)",
    )


async def generate_and_store(
    recap: GameNightRecap,
    games: list[NightGame],
    summaries: GameNightSummaryRepo,
) -> None:
    """Generate this night's recap and persist it. **Spends a real LLM call.**

    Callers own the decision to spend - this checks nothing about whether a row
    already exists, so a deliberate regeneration works. ``match_count`` is
    stored from the recap the text was actually written from, so a night that
    later gains a late upload can be recognised as under-described without
    re-reading the text.
    """
    async with generation_lock:
        text = await asyncio.to_thread(generate_summary, recap, games)
        summaries.save_night_summary(
            recap.date, text, llm.active_provider(), recap.match_count
        )
