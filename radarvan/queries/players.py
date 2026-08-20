"""Player read models - results shared by a route and at least one other caller.

These build `api_types` objects, which is normally a route's job. They live here
because they have a second consumer: `commentary.matchup_commentary` needs the
same ratings payload and the same head-to-head detail that `/api/player_ratings/`
and `/api/player_head_to_head/` return, and it used to get them by *calling the
route handlers as functions* - passing `replay_manager=` into an HTTP handler and
`asyncio.run`-ing an endpoint. That made the handler signature part of an internal
API, so narrowing it (step 06) broke a module three layers away.

The rule this follows: a handler may build its own response inline, right up until
something other than HTTP wants the same answer. At that point the answer is a read
model and belongs here, with the handler reduced to selecting a corpus and calling
it.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .. import head_to_head, match_details, player_ids, player_rating
from ..api_types import (
    HeadToHeadDetail,
    MatchInfo,
    PlayerName,
    PlayerRatingData,
    PlayerRatings,
    ShortPlayerRating,
)
from ..dependencies import db_manager

# How many of a pair's most recent shared games get kill data loaded for the
# value-destroyed figures. Windowed because for the handful of extremely
# long-running pairs (600+ shared games), even a single batched query transfers
# enough kill-event JSON over the (remote) DB connection to take several seconds.
H2H_VALUE_WINDOW = 40


def player_ratings_payload(game_list: list[MatchInfo]) -> PlayerRatingData:
    """Ratings, rating history, and recent form over `game_list`."""
    ratings_and_counts = player_rating.compute_player_ratings(game_list)
    counts = ratings_and_counts.game_counts

    today = datetime.now(UTC).date()
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)
    thirty_days_ago = today - timedelta(days=30)

    cutoffs = [(7, seven_days_ago), (14, fourteen_days_ago), (30, thirty_days_ago)]

    def convert(rating: player_rating.NamedRating) -> PlayerRatings:
        deltas: dict[int, float] = {7: 0.0, 14: 0.0, 30: 0.0}
        for c in ratings_and_counts.daily_changes.get(rating.name, []):
            for days, cutoff in cutoffs:
                if c.date >= cutoff:
                    deltas[days] += c.delta
        return PlayerRatings(
            name=rating.name,
            ordinal=rating.ordinal(),
            mu=rating.mu,
            sigma=rating.sigma,
            atdate=rating.at_date,
            game_count=counts.get(rating.name),
            recent_deltas={k: v for k, v in deltas.items() if v != 0},
            high_ordinal=ratings_and_counts.ordinal_high.get(rating.name),
            low_ordinal=ratings_and_counts.ordinal_low.get(rating.name),
        )

    def convert_short(rating: player_rating.NamedRating) -> ShortPlayerRating:
        return ShortPlayerRating(
            mu=rating.mu,
            sigma=rating.sigma,
            atdate=rating.at_date,
        )

    player_results: dict[str, list[bool]] = defaultdict(list)
    for game in sorted(game_list, key=lambda g: g.timestamp):
        for p in game.roster().participants:
            player_results[player_ids.resolve_player_name(p.name, p.color)].append(
                p.won
            )
    rated_names = {r.name for r in ratings_and_counts.ratings}
    player_form = {
        name: results[-10:]
        for name, results in player_results.items()
        if name in rated_names
    }

    converted = [convert(r) for r in ratings_and_counts.ratings]
    over_time = {
        name: [convert_short(r) for r in ratings]
        for name, ratings in ratings_and_counts.over_time.items()
    }
    return PlayerRatingData(
        player_rating=converted,
        player_rating_overtime=over_time,
        player_form=player_form,
    )


async def player_head_to_head_detail(
    game_list: list[MatchInfo], player1: PlayerName, player2: PlayerName
) -> HeadToHeadDetail:
    """Detailed head-to-head record between two players (opposite-team games only).

    Considers competitive games where both players took part on *different* teams;
    the winner of each game is the side whose team won. Aggregates the overall
    record, each player's record by the general they piloted, and the record by
    map, plus the full game list (most recent first).

    Also loads kill data for the most recent `H2H_VALUE_WINDOW` games featuring
    both players, to compute value destroyed between them.
    """
    # Ask the roster, not every slot: a spectator whose account resolves to one
    # of these names would otherwise make a game they never played a candidate.
    # `participants` matches what compute_head_to_head itself reads.
    candidate_games = [
        g
        for g in game_list
        if {player1, player2}
        <= {
            player_ids.resolve_player_name(p.name, p.color)
            for p in g.roster().participants
        }
    ]
    candidate_games.sort(key=lambda g: g.timestamp, reverse=True)
    candidate_ids = [g.id for g in candidate_games[:H2H_VALUE_WINDOW]]
    kill_data_by_match = await match_details.load_many_kill_data(
        candidate_ids, db_manager
    )
    value_by_match = head_to_head.value_destroyed_by_match(
        kill_data_by_match, player1, player2
    )
    return head_to_head.compute_head_to_head(
        game_list, player1, player2, value_by_match
    )
