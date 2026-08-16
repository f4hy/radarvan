"""Post-game set recap: given a completed bracket match and the games that
were played in it, feed every game's full match details to the active LLM
provider and return a game-by-game write-up ending in a punchy recap of the
result.

The counterpart to ``matchup_commentary``, and deliberately narrower: the
pre-game blurb pulls lifetime profiles, head-to-head and ratings because it
has to guess at a set that hasn't happened; the recap only needs the games
themselves, which are a complete account of what it's describing. Anything
lifetime would just invite the model to explain the result with history
instead of reading the match.

Details come through ``cache.details_from_id`` - the same two-tier cache
``/api/details`` serves, so a set whose games anyone has already looked at
costs nothing extra to summarize.

Like ``matchup_commentary``, this module always regenerates; the cache
check/write lives at the route layer (routes/commentary.py), keyed on the
durable tournament + bracket stage via
``repositories.commentary.BracketSummaryRepo``. Unlike the pre-game blurb,
that key can't go stale in the ordinary case: a completed set's games don't
change. It *can* if an admin relinks games afterwards, which is what
``force_refresh`` is for.
"""

from __future__ import annotations

import structlog

from ..api_types import BracketMatchOutput, MatchInfo
from ..cache import details_from_id
from ..db_utils import ReplayManager
from . import llm, summary_data
from .summary_prompts import RECAP_GUIDELINES

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = RECAP_GUIDELINES


def build_user_message(summary: summary_data.SummarySet) -> str:
    """Assemble the user turn: the ask plus the whole set, rendered as plain
    text (see ``summary_data``'s module docstring). Kept separate from
    ``build_prompt`` so it's unit-testable without a DB or a network call."""
    note = summary_data.missing_games_note(summary)
    note_block = f"{note}\n\n" if note else ""
    return (
        f"Write the post-game recap for {summary.round_name}: "
        f"{summary.player_a} vs {summary.player_b}.\n\n"
        f"{note_block}"
        "<set_result>\n"
        f"{summary_data.render_summary_set(summary)}\n"
        "</set_result>"
    )


def build_set(
    replay_manager: ReplayManager,
    bracket_match: BracketMatchOutput,
    games: list[MatchInfo],
) -> summary_data.SummarySet:
    """Load every game's details and reduce the set to recap-ready shape.

    ``games`` must be the set's linked games in the order they were played -
    the route reads them from the tournament link table, which is the stored
    fact about which games count (see routes/bracket.get_bracket_games).
    """
    built = []
    for match in games:
        game = summary_data.build_summary_game(
            match, details_from_id(match.id, replay_manager)
        )
        if game is None:
            logger.info(
                "skipping game with no clean 1v1 result",
                match_id=match.id,
                stage=bracket_match.match_id,
            )
            continue
        built.append(game)
    return summary_data.build_summary_set(bracket_match, built)


def build_prompt(
    replay_manager: ReplayManager,
    bracket_match: BracketMatchOutput,
    games: list[MatchInfo],
) -> llm.Prompt:
    """The exact system + user content that would be sent to the active LLM
    provider for this set - without calling the API."""
    summary = build_set(replay_manager, bracket_match, games)
    return llm.Prompt(system=SYSTEM_PROMPT, user_message=build_user_message(summary))


def generate_summary(
    replay_manager: ReplayManager,
    bracket_match: BracketMatchOutput,
    games: list[MatchInfo],
) -> str:
    """Generate the post-game recap for one completed bracket match, using
    whichever provider COMMENTARY_PROVIDER selects."""
    prompt = build_prompt(replay_manager, bracket_match, games)
    return llm.generate(
        prompt,
        kind="Post-game summary",
        label=(
            f"{bracket_match.player_a} vs {bracket_match.player_b} "
            f"({bracket_match.round_name})"
        ),
    )
