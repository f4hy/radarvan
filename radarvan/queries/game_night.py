"""Corpus selection and loading for one game night.

The read model behind the recap page. It lives here rather than in the route
because the scheduler needs the same answer: the nightly summary job has to
describe exactly the games the page shows, and rebuilding that selection a
second time in ``schedule.py`` is how a prompt ends up talking about a
different night than the reader is looking at. Import direction stays
``routes`` -> ``queries`` -> ``cache``/``repositories`` (see CLAUDE.md).

Nothing here spends an LLM call; generation is ``commentary/night_summary``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

from .. import game_night, match_details, match_narrative, player_rating, utils
from ..api_types import GameNightRecap, MatchDetails, MatchInfo, MatchNarrative
from ..db_utils import DatabaseManager
from typing import NamedTuple


class NightGames(NamedTuple):
    """One night's games and their details, as the recap and the prompt see them.

    Returned together because the two callers need the same three things and
    must not re-derive any of them independently: the recap the page renders,
    the counted games it was computed over, and the details those games'
    narratives come from.
    """

    recap: GameNightRecap
    counted: list[MatchInfo]
    details_by_id: dict[int, MatchDetails]


def on_night(games: list[MatchInfo], night: date) -> list[MatchInfo]:
    """This night's games, in the order they were played.

    ``MatchInfo.date`` is already the game-night key (``utils.game_night_date``
    - US Eastern with a 5am rollover), so an evening that ran past midnight is
    one night here rather than two.
    """
    return sorted(
        (game for game in games if game.date == night),
        key=lambda game: game.timestamp,
    )


async def details_for(
    matches: list[MatchInfo], db_manager: DatabaseManager
) -> dict[int, MatchDetails]:
    """Cached details for each match, keyed by id, skipping unparsed ones.

    Goes through the bounded-concurrency loader rather than a loop of
    ``details_from_id``: on a cold cache each miss is an S3 fetch and a parse,
    and a fifteen-game night would otherwise block the event loop for all of
    them in series.
    """
    loaded = await match_details.load_many_match_details(
        [match.id for match in matches], db_manager
    )
    return {details.match_id: details for details in loaded}


async def build_night_recap(
    night: date,
    all_games: list[MatchInfo],
    competitive: list[MatchInfo],
    db_manager: DatabaseManager,
) -> NightGames:
    """The deterministic recap for one night, plus what it was built from."""
    tonight = on_night(all_games, night)
    counted = on_night(competitive, night)
    details_by_id = await details_for(counted, db_manager)
    # Ratings are @derived over the corpus and usually warm, but a cold call is
    # a full pass over every competitive game - keep it off the event loop.
    ratings = await asyncio.to_thread(player_rating.compute_player_ratings, competitive)
    recap = await asyncio.to_thread(
        game_night.build_recap,
        night,
        tonight,
        counted,
        details_by_id,
        ratings.upsets,
    )
    return NightGames(recap=recap, counted=counted, details_by_id=details_by_id)


def night_narratives(night_games: NightGames) -> list[MatchNarrative]:
    """A narrative per counted game, in play order - the model's game-by-game input."""
    return [
        match_narrative.build_narrative(match, night_games.details_by_id.get(match.id))
        for match in night_games.counted
    ]


def latest_closed_night(all_games: list[MatchInfo]) -> date | None:
    """The most recent game night that has finished, by the app's own clock.

    "Finished" means its key is behind the night currently in progress -
    ``utils.game_night_date`` rolls over at 5am US Eastern, so a caller running
    before then would otherwise pick the evening people are still playing.
    """
    tonight = utils.game_night_date_of(datetime.now(UTC))
    played = [game.date for game in all_games if game.date < tonight]
    return max(played) if played else None
