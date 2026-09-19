"""LLM-written caption for the night's most interesting matches.

Only the nightly job and the ops endpoint generate; the read path attaches a
stored blurb or shows none.
"""

from __future__ import annotations

import asyncio
from typing import NamedTuple

import structlog

from .. import match_narrative
from ..api_types import MatchBlurbBackfillNight, MatchBlurbRun, MatchNarrative
from ..match_interest import (
    MIN_INTEREST_FOR_BLURB,
    Interest,
    ScoredMatch,
    rank,
)
from ..queries.game_night import NightGames
from ..repositories import MatchBlurbRepo
from . import llm
from .match_prompts import MATCH_GUIDELINES
from .night_summary import render_timeline, tournament_tag

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = MATCH_GUIDELINES

# The most calls one night can cost.
MAX_BLURBS_PER_NIGHT = 3

# Held across the nightly job and the ops endpoint so neither bills for the same match twice.
generation_lock = asyncio.Lock()


def pick_candidates(night_games: NightGames) -> list[ScoredMatch]:
    ranked = rank(night_games.counted, night_games.details_by_id)
    above_bar = [s for s in ranked if s.interest.score >= MIN_INTEREST_FOR_BLURB]
    return above_bar[:MAX_BLURBS_PER_NIGHT]


def render_match(narrative: MatchNarrative, interest: Interest) -> str:
    lineup = next((b.text for b in narrative.beats if b.kind == "setup"), None)
    timeline = render_timeline(narrative, "  ")
    sections = [f"THE GAME\n  {tournament_tag(narrative)}{narrative.headline}"]
    if lineup is not None:
        sections.append(f"LINEUP\n  {lineup}")
    if timeline:
        sections.append("WHAT HAPPENED\n" + "\n".join(timeline))
    sections.append(
        'WHY THIS GAME WAS PICKED ("they" = the winners)\n'
        + "\n".join(f"  {r}" for r in interest.reasons)
    )
    return "\n\n".join(sections)


def build_prompt(narrative: MatchNarrative, interest: Interest) -> llm.Prompt:
    """What would be sent, without calling the API."""
    return llm.Prompt(
        system=SYSTEM_PROMPT,
        user_message=(
            "Write the caption for this game.\n\n"
            f"<game>\n{render_match(narrative, interest)}\n</game>"
        ),
    )


def generate_blurb(narrative: MatchNarrative, interest: Interest) -> str:
    """Spends a real LLM call."""
    return llm.generate(
        build_prompt(narrative, interest),
        kind="Match blurb",
        label=f"match {narrative.match_id}",
    )


async def generate_night_blurbs(
    night_games: NightGames,
    blurbs: MatchBlurbRepo,
    *,
    force: bool = False,
    max_calls: int | None = None,
) -> MatchBlurbRun:
    """Caption this night's picks that lack a blurb (all of them with ``force``).

    Spends a real LLM call per id in ``generated``, at most ``max_calls`` of them.
    Each blurb is stored as it is written; a provider error propagates, keeping
    what was already paid for.
    """
    picks = pick_candidates(night_games)
    generated: list[int] = []
    async with generation_lock:
        have = set() if force else set(blurbs.get_blurbs(p.match.id for p in picks))
        for pick in picks:
            if pick.match.id in have:
                continue
            if max_calls is not None and len(generated) >= max_calls:
                break
            narrative = match_narrative.build_narrative(pick.match, pick.details)
            text = await asyncio.to_thread(generate_blurb, narrative, pick.interest)
            blurbs.save_blurb(pick.match.id, text, llm.active_provider())
            generated.append(pick.match.id)
    logger.info("match blurbs written", generated=generated, picked=len(picks))
    return MatchBlurbRun(
        date=night_games.recap.date,
        picked=[p.match.id for p in picks],
        generated=generated,
    )


class NightCaptions(NamedTuple):
    report: MatchBlurbBackfillNight
    failed: bool


async def caption_night(
    night_games: NightGames, blurbs: MatchBlurbRepo, max_calls: int
) -> NightCaptions:
    """One night of a backfill: spend up to ``max_calls`` (0 spends nothing) and report.

    Counts come from what is stored, so a provider error part-way still reports
    the blurbs written before it.
    """
    picked = [p.match.id for p in pick_candidates(night_games)]
    before = len(blurbs.get_blurbs(picked))
    failed = False
    if max_calls > 0:
        try:
            await generate_night_blurbs(night_games, blurbs, max_calls=max_calls)
        except llm.CommentaryGenerationError:
            logger.exception(
                "match blurb backfill stopped", night=str(night_games.recap.date)
            )
            failed = True
    have = len(blurbs.get_blurbs(picked))
    report = MatchBlurbBackfillNight(
        date=night_games.recap.date,
        picked=len(picked),
        generated=have - before,
        pending=len(picked) - have,
    )
    return NightCaptions(report, failed)
