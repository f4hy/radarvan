"""Corpus selection: which games a request is about.

Almost every stats handler in this codebase opened the same way - pick one of the
two match sets, then narrow it:

    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)
    game_list = matches.filter_by_months_back(game_list, months_back)

Three lines, repeated across sixteen handlers, deciding the single thing most
likely to make two endpoints quietly disagree: *which games count*. That decision
lives here now, and the handlers are left with what they are actually for -
mapping a result onto the wire.

The functions come in pairs. The plain ones (`competitive_games`, `all_games`)
take a `ReplayManager` and are callable from anywhere - background jobs, other
queries, tests. The `Annotated` aliases below wrap them as FastAPI dependencies so
a handler can declare the corpus it needs *in its signature* and never see a
database object at all:

    def get_player_skills(games: CompetitiveGames) -> list[PlayerSkill]:

That is the narrowing step 06 asks for, arrived at from the other direction: not
"a smaller repository", but no repository - a handler that computes over games has
no business holding something that can write to the database.

**Do not reach for the dependency form when a handler can avoid the work.** A
FastAPI dependency is resolved before the handler runs, so a corpus declared this
way is always selected, even on a path that would have returned early.
`routes/players.balance_teams` is the live example: its six-hour hold answers most
requests without touching the corpus at all, so it keeps the `ReplayManager` and
calls the plain function lazily on a miss.
"""

from typing import Annotated

from fastapi import Depends, Query

from .. import matches
from ..api_types import MatchInfo
from ..cache import competitive_matches, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

# One wording, so the generated client documents the same thing everywhere. The
# per-route strings this replaced disagreed about whether 1v1 was accepted; it is
# - `competitive_matches` keeps 1v1s (a 1v1 has is_team_game=True), and
# `filter_by_format` matches on `composition.category` regardless.
FORMAT_DESCRIPTION = "Filter by game format: 1v1, 2v2, 3v3, 4v4"
MONTHS_BACK_DESCRIPTION = "Only use matches from the last N months"


def _narrow(
    games: list[MatchInfo], game_format: str | None, months_back: int | None
) -> list[MatchInfo]:
    return matches.filter_by_months_back(
        matches.filter_by_format(games, game_format), months_back
    )


def competitive_games(
    replay_manager: ReplayManager,
    *,
    game_format: str | None = None,
    months_back: int | None = None,
) -> list[MatchInfo]:
    """The rated corpus: complete, balanced, non-comp-stomp, known players.

    What W/L records, ratings, synergy and skills are computed over. See the
    "two match sets" note in CLAUDE.md for how this differs from `all_games`.
    """
    return _narrow(
        list(competitive_matches(replay_manager).values()), game_format, months_back
    )


def all_games(
    replay_manager: ReplayManager,
    *,
    game_format: str | None = None,
    months_back: int | None = None,
) -> list[MatchInfo]:
    """Every deduplicated match, including the ones no leaderboard counts.

    For counts and listings - "how many games has this player played" includes
    the comp-stomps and the unbalanced ones.
    """
    return _narrow(
        list(sorted_deduped_matches(replay_manager).values()), game_format, months_back
    )


def _competitive_dep(
    game_format: str | None = Query(None, description=FORMAT_DESCRIPTION),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MatchInfo]:
    return competitive_games(replay_manager, game_format=game_format)


def _competitive_windowed_dep(
    game_format: str | None = Query(None, description=FORMAT_DESCRIPTION),
    months_back: int | None = Query(None, ge=1, description=MONTHS_BACK_DESCRIPTION),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MatchInfo]:
    return competitive_games(
        replay_manager, game_format=game_format, months_back=months_back
    )


def _all_competitive_dep(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MatchInfo]:
    return competitive_games(replay_manager)


def _all_games_dep(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MatchInfo]:
    return all_games(replay_manager)


# The corpus a handler declares it needs. The `game_format` query parameter comes
# with the dependency, so a route that takes `CompetitiveGames` advertises it in
# the OpenAPI spec without restating it.
CompetitiveGames = Annotated[list[MatchInfo], Depends(_competitive_dep)]
WindowedCompetitiveGames = Annotated[
    list[MatchInfo], Depends(_competitive_windowed_dep)
]
UnfilteredCompetitiveGames = Annotated[list[MatchInfo], Depends(_all_competitive_dep)]
AllGames = Annotated[list[MatchInfo], Depends(_all_games_dep)]
