"""Pre-game matchup commentary: given two players and a round description,
use ``commentary_prompts.GUIDELINES`` as the system prompt and the two
players' actual profile/head-to-head data as the user message, call
whichever LLM provider is active, and return the generated commentary text.

The provider call itself (selection, budget, usage logging, notification)
lives in ``llm`` - shared with the post-game recap in ``postgame_summary``.

Data fetch deliberately calls the existing route handler functions directly
(``radarvan.routes.profile.get_player_profile``,
``radarvan.routes.players.get_player_head_to_head``,
``radarvan.routes.players.get_player_ratings``) rather than re-deriving the
same games/synergy/rating assembly and calling the lower-level logic those
routes wrap. This inverts the usual "routes depend on logic modules"
direction on purpose: any future improvement to those endpoints - new
fields, better computation, bug fixes - flows into commentary generation
automatically instead of drifting out of sync with a second implementation.
The fetched ``PlayerProfile``/``HeadToHeadDetail``/``PlayerRatingData`` are
then reduced to ``hype_data.HypePlayerData``/``HypeHeadToHead``/
``HypeRatingsContext`` - purpose-built shapes holding only what the
guidelines reference, rendered as plain text rather than JSON (see
``hype_data``'s module docstring for why).

``_tournament_inputs`` adds the same treatment for the bracket itself
(``routes.bracket.get_bracket`` + ``routes.tournaments.tournament_games_for``),
giving the model what has already happened in the tournament being played -
each player's completed sets, and the individual games behind them.

This module always regenerates - the cache check/write lives at the route
layer (routes/commentary.py), keyed on (player1, player2, round_name) via
repositories.commentary.MatchupCommentaryRepo, so this module and its
callers stay unaware caching exists.

**Known staleness**: that cache key has no time component, while the
tournament block does change as the tournament progresses. A blurb generated
the moment a matchup became visible is frozen with whatever had been played
then, and is served unchanged afterwards. Regenerating with
``force_refresh=true`` (admin-tier) is the current answer; giving the key a
component that moves when a linked game lands would be the real one.
"""

from __future__ import annotations

import asyncio

import structlog

from ..api_types import BracketTournamentOutput, MatchInfo
from ..db_utils import ReplayManager
from ..repositories import BracketRepo
from ..routes import bracket as bracket_routes
from ..routes import players as players_routes
from ..routes import profile as profile_routes
from ..routes import tournaments as tournaments_routes
from . import hype_data, llm
from .commentary_prompts import GUIDELINES
from typing import NamedTuple

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = GUIDELINES

# Re-exported so callers of this module (the route, its tests) don't need to
# know the provider plumbing moved to `llm`.
PROVIDER_ENV = llm.PROVIDER_ENV
MatchupPrompt = llm.Prompt
CommentaryGenerationError = llm.CommentaryGenerationError
active_provider = llm.active_provider
commentary_available = llm.commentary_available


def build_user_message(
    round_name: str,
    player1: str,
    player2: str,
    player1_data: hype_data.HypePlayerData,
    player2_data: hype_data.HypePlayerData,
    h2h_1v1: hype_data.HypeHeadToHead,
    h2h_all: hype_data.HypeHeadToHead,
    ratings_context: hype_data.HypeRatingsContext,
    tournament_context: hype_data.HypeTournamentContext | None = None,
) -> str:
    """Assemble the user turn: the ask plus every data payload, clearly
    labeled. Kept separate from generate_commentary so it's unit-testable
    without a network call. Payloads are rendered as plain text (see
    hype_data's module docstring), not JSON.

    ``tournament_context`` leads, ahead of the lifetime profile data: it's
    the only block about the competition actually being played, and the
    lifetime numbers behind it are team-game history the players already
    know. It's dropped entirely when there's nothing in it (no bracket, or
    neither player has finished a set yet) rather than included empty.
    """
    tournament_block = ""
    if tournament_context is not None:
        rendered = hype_data.render_tournament_context(tournament_context)
        if rendered:
            tournament_block = (
                f"<tournament_so_far>\n{rendered}\n</tournament_so_far>\n\n"
            )
    return (
        f"Generate the pre-game hype commentary for {round_name}: {player1} vs {player2}.\n\n"
        f"{tournament_block}"
        f'<player1_profile player="{player1}">\n'
        f"{hype_data.render_player_data(player1_data)}\n"
        "</player1_profile>\n\n"
        f'<player2_profile player="{player2}">\n'
        f"{hype_data.render_player_data(player2_data)}\n"
        "</player2_profile>\n\n"
        "<head_to_head_1v1>\n"
        f"{hype_data.render_head_to_head(h2h_1v1)}\n"
        "</head_to_head_1v1>\n\n"
        "<head_to_head_all_formats>\n"
        f"{hype_data.render_head_to_head(h2h_all)}\n"
        "</head_to_head_all_formats>\n\n"
        "<team_game_ratings>\n"
        f"{hype_data.render_ratings_context(ratings_context)}\n"
        "</team_game_ratings>"
    )


class TournamentInputs(NamedTuple):
    """The resolved (possibly redacted) bracket and the games linked to it."""

    bracket_output: BracketTournamentOutput | None
    tournament_games: list[MatchInfo]


def _tournament_inputs(
    replay_manager: ReplayManager,
) -> TournamentInputs:
    """The resolved bracket and every game linked to it.

    Both come from the existing route handlers for the same reason the
    profile/head-to-head pulls do (see the module docstring) - ``get_bracket``
    in particular owns the pre-reveal redaction, so routing through it means
    unrevealed placements can't reach a prompt by way of this module
    forgetting to check.

    ``user=None`` (never a preview) is deliberate: commentary is served to
    everyone from one cache row, so it must only ever be built from what
    everyone can already see.
    """
    bracket_repo = BracketRepo(replay_manager.session)
    bracket_output = bracket_routes.get_bracket(
        preview=False, user=None, repo=bracket_repo
    )
    if bracket_output is None:
        return TournamentInputs(bracket_output=None, tournament_games=[])

    active = bracket_repo.get_active()
    if active is None or active.tournament_id is None:
        # A bracket that has never been through sync_links has no registry
        # row, so no games are linked to it yet - the set results on the
        # bracket itself are still worth having.
        return TournamentInputs(bracket_output=bracket_output, tournament_games=[])
    parent = replay_manager.get_tournament_by_id(active.tournament_id)
    if parent is None:
        return TournamentInputs(bracket_output=bracket_output, tournament_games=[])
    games = tournaments_routes.tournament_games_for(
        slug=parent.slug,
        replay_manager=replay_manager,
        tournament_repo=replay_manager,
    )
    return TournamentInputs(
        bracket_output=bracket_output, tournament_games=games.matches
    )


def build_prompt(
    replay_manager: ReplayManager, player1: str, player2: str, round_name: str
) -> MatchupPrompt:
    """Fetch both players' data and assemble the system + user content that
    would be sent to the active LLM provider for round_name - without
    calling the API. Identical regardless of which provider is active.

    player1/player2 must already be alias-resolved - the PlayerName-typed
    query params on routes/commentary.py handle this before it reaches here.
    """
    profile1 = profile_routes.get_player_profile(
        player=player1, replay_manager=replay_manager
    )
    profile2 = profile_routes.get_player_profile(
        player=player2, replay_manager=replay_manager
    )
    # Team-game rating is fetched once for the whole population: per-player
    # recent form (plain W/L) goes in each profile block, while the ordinals
    # themselves go into one whole-population calibration block instead of
    # being embedded per-player - see hype_data.HypeRatingsContext's
    # docstring for why.
    ratings = players_routes.get_player_ratings(
        game_format=None, months_back=None, replay_manager=replay_manager
    )
    ratings_context = hype_data.build_hype_ratings_context(
        ratings.player_rating, player1, player2
    )
    # get_player_head_to_head is async (it loads kill data for value
    # destroyed) but build_prompt is always called from a sync context (a
    # sync FastAPI route runs in starlette's threadpool, with no event loop
    # of its own) - asyncio.run() bridges that safely here.
    h2h_1v1 = asyncio.run(
        players_routes.get_player_head_to_head(
            player1=player1,
            player2=player2,
            game_format="1v1",
            replay_manager=replay_manager,
        )
    )
    h2h_all = asyncio.run(
        players_routes.get_player_head_to_head(
            player1=player1,
            player2=player2,
            game_format=None,
            replay_manager=replay_manager,
        )
    )
    bracket_output, tournament_games = _tournament_inputs(replay_manager)
    user_message = build_user_message(
        round_name,
        player1,
        player2,
        hype_data.build_hype_player_data(
            profile1, ratings.player_form.get(player1, [])
        ),
        hype_data.build_hype_player_data(
            profile2, ratings.player_form.get(player2, [])
        ),
        hype_data.build_hype_head_to_head(h2h_1v1),
        hype_data.build_hype_head_to_head(h2h_all),
        ratings_context,
        hype_data.build_hype_tournament_context(
            bracket_output, tournament_games, player1, player2
        ),
    )
    return MatchupPrompt(system=SYSTEM_PROMPT, user_message=user_message)


def generate_commentary(
    replay_manager: ReplayManager, player1: str, player2: str, round_name: str
) -> str:
    """Fetch both players' data and generate pre-game commentary for
    round_name, using whichever provider COMMENTARY_PROVIDER selects."""
    prompt = build_prompt(replay_manager, player1, player2, round_name)
    return llm.generate(
        prompt, kind="Matchup commentary", label=f"{player1} vs {player2}"
    )
