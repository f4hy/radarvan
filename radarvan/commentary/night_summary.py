"""The once-a-night, LLM-written game-night recap.

The third generator in this package, and the cheapest to feed: where the
bracket recap reduces raw ``MatchDetails`` itself (``summary_data``), this one
is handed work already done - the deterministic recap from ``game_night`` and
one ``MatchNarrative`` per game from ``match_narrative``. Both of those exist
because the page shows them, so the prompt is a rendering of what a reader
already sees rather than a second, parallel reduction of the same replays that
could drift from it.

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
from datetime import datetime

import structlog

from ..api_types import GameNightRecap, MatchNarrative
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


def _render_narrative(narrative: MatchNarrative) -> list[str]:
    stamp = f"{_local(narrative.started_at)} - " if narrative.started_at else ""
    label = f"[TOURNAMENT: {narrative.tournament}] " if narrative.tournament else ""
    lines = [f"  {stamp}{label}{narrative.headline}"]
    for beat in narrative.beats:
        # The setup beat restates the lineup the headline already carries, and
        # the result beat restates the result - both are noise once the
        # headline is there.
        if beat.kind in {"setup", "result"}:
            continue
        stamp = f"{beat.at_minute:.1f}min - " if beat.at_minute is not None else ""
        lines.append(f"    {stamp}{beat.text}")
    return lines


def render_night(recap: GameNightRecap, narratives: list[MatchNarrative]) -> str:
    """The night as plain labelled text - the same convention as ``summary_data``.

    Rendered rather than serialized as JSON because nothing downstream
    re-parses it, and prose-shaped input is what the model is being asked to
    write from.
    """
    sections: list[str] = []

    shape = [f"Games played: {recap.match_count}"]
    if recap.counted_matches != recap.match_count:
        shape.append(
            f"Of those, {recap.counted_matches} were decided competitive games "
            "(the rest were unfinished, comp-stomps, or otherwise uncounted)."
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

    if narratives:
        blocks = []
        for index, narrative in enumerate(narratives[:MAX_GAMES_RENDERED], start=1):
            blocks.append(f"Game {index}:\n" + "\n".join(_render_narrative(narrative)))
        sections.append("GAME BY GAME\n" + "\n\n".join(blocks))

    return "\n\n".join(sections)


def build_user_message(recap: GameNightRecap, narratives: list[MatchNarrative]) -> str:
    """Assemble the user turn. Separate from ``build_prompt`` so it is
    unit-testable without a DB or a network call."""
    return (
        f"Write the game-night recap for {recap.date:%A %-d %B %Y}.\n\n"
        "<game_night>\n"
        f"{render_night(recap, narratives)}\n"
        "</game_night>"
    )


def build_prompt(recap: GameNightRecap, narratives: list[MatchNarrative]) -> llm.Prompt:
    """The exact system + user content that would be sent to the active
    provider for this night - without calling the API."""
    return llm.Prompt(
        system=SYSTEM_PROMPT, user_message=build_user_message(recap, narratives)
    )


def generate_summary(recap: GameNightRecap, narratives: list[MatchNarrative]) -> str:
    """Generate the recap for one game night, using whichever provider
    COMMENTARY_PROVIDER selects. Always spends a real call - see the module
    docstring for who is allowed to call this."""
    prompt = build_prompt(recap, narratives)
    return llm.generate(
        prompt,
        kind="Game night recap",
        label=f"{recap.date} ({recap.match_count} games)",
    )


async def generate_and_store(
    recap: GameNightRecap,
    narratives: list[MatchNarrative],
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
        text = await asyncio.to_thread(generate_summary, recap, narratives)
        summaries.save_night_summary(
            recap.date, text, llm.active_provider(), recap.match_count
        )
