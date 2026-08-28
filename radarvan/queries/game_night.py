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
from datetime import UTC, date, datetime, timedelta

from .. import game_night, match_details, match_narrative, player_rating, utils
from ..api_types import GameNightRecap, MatchDetails, MatchInfo, MatchNarrative, Team
from ..db_utils import DatabaseManager
from typing import NamedTuple


class NightGames(NamedTuple):
    """One night's games and their details, as the recap and the prompt see them.

    Returned together because the two callers need the same things and must not
    re-derive any of them independently: the recap the page renders, every game
    that was played, the subset the records were computed over, and the details
    the narratives come from.

    ``played`` and ``counted`` are both here because they answer different
    questions and the prompt needs both. The standings and the highlight cards
    are only honest over ``counted``; the *clock* is only honest over
    ``played``. Handing the model narratives for ``counted`` alone left holes in
    the timeline where the uncounted games had been, and it read those holes as
    downtime - one night's recap described a 29-minute free-for-all as a
    "40-minute breather".
    """

    recap: GameNightRecap
    played: list[MatchInfo]
    counted: list[MatchInfo]
    details_by_id: dict[int, MatchDetails]


class NightGame(NamedTuple):
    """One game as the prompt sees it: its story, and whether it counts.

    The ``uncounted`` reason lives here rather than on ``MatchNarrative``
    because it is not a property of the match - it is this night's answer to
    "is this game in the standings above", and deriving it a second time
    anywhere else is how the prompt starts describing a different night than
    the page (the reason ``build_night_recap`` exists at all).
    """

    narrative: MatchNarrative
    # None when the game is in the standings; otherwise why it isn't, in words
    # the model can use ("free-for-all", "comp-stomp", ...).
    uncounted: str | None


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
    # The decided subset is what the standings and the highlight cards are
    # computed over, so it is what `counted` has to mean everywhere downstream.
    # `build_recap` applies the same filter to whatever it is handed, so
    # narrowing here changes nothing it produces - it just stops the prompt
    # from having to re-derive the set the page was built from.
    counted = [
        match
        for match in on_night(competitive, night)
        if match.winning_team > Team.NONE
    ]
    # Details for every game, not just the counted ones: an uncounted game is
    # still an hour of somebody's evening and still has a story worth telling
    # (a free-for-all is usually the most memorable game of the night). The
    # loader is concurrency-bounded, so a handful of extra ids is cheap.
    details_by_id = await details_for(tonight, db_manager)
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
    return NightGames(
        recap=recap, played=tonight, counted=counted, details_by_id=details_by_id
    )


def uncounted_reason(match: MatchInfo) -> str:
    """Why this game is outside the standings, in words rather than a flag.

    Only ever asked of a game already known to be uncounted. The order is the
    order a reader would explain it in, not ``competitive_game_filter``'s: a
    free-for-all also fails "balanced" and "team game", and "free-for-all" is
    the answer that lets the model write about it correctly, where "uneven
    teams" would invite it to describe a lopsided 3v1 that never happened.
    """
    composition = match.composition
    if composition is None:
        return "not parsed"
    if composition.is_ffa:
        return "free-for-all"
    if composition.is_comp_stomp:
        return "comp-stomp"
    if composition.num_computers > 1:
        return "more than one AI"
    if match.winning_team <= Team.NONE:
        return match.incomplete or "no result recorded"
    if not composition.is_balanced:
        return "uneven teams"
    if not composition.is_team_game:
        return "not a team game"
    return "not counted"


def night_narratives(night_games: NightGames) -> list[NightGame]:
    """A narrative per game played, in play order - the model's game-by-game input.

    Every game, not just the counted ones, because this list is the only place
    the prompt carries a clock: dropping a game leaves a gap the model can
    only read as people having stopped playing. The uncounted ones come
    labelled with why, so their results stay out of the standings the model
    quotes while their beats stay available to it.
    """
    counted_ids = {match.id for match in night_games.counted}
    return [
        NightGame(
            narrative=match_narrative.build_narrative(
                match, night_games.details_by_id.get(match.id)
            ),
            uncounted=None if match.id in counted_ids else uncounted_reason(match),
        )
        for match in night_games.played
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


def closed_nights_within(all_games: list[MatchInfo], days: int) -> list[date]:
    """The finished game nights of the last ``days``, newest first.

    The window is counted in game-night keys back from the night currently in
    progress, which is excluded for the same reason ``latest_closed_night``
    excludes it: a stored recap is permanent, so an evening still being played
    must never be summarized. Nights with no games simply aren't in the list.
    """
    tonight = utils.game_night_date_of(datetime.now(UTC))
    earliest = tonight - timedelta(days=days)
    nights = {game.date for game in all_games if earliest <= game.date < tonight}
    return sorted(nights, reverse=True)
