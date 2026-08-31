"""Balanced team construction - enumerates team splits and uses player ratings (with
hand-tuned synergy adjustments for certain pairings) to pick the most even matchup."""

from collections.abc import Iterable, Iterator, Mapping
from itertools import combinations
from . import player_ids
from openskill.models import PlackettLuceRating
from radarvan.api_types import MatchInfo
import structlog
from .derived import CORPUS, derived
from .player_rating import RatingsAndCounts, compute_player_ratings, get_model

logger = structlog.get_logger(__name__)


# Pairs that, when on the same team, are treated as slightly more balanced.
# Value is a scale factor applied to the advantage (distance from 0.5):
# win_pct = 0.5 + (win_pct - 0.5) * scale - 0.85 reduces a 10-point edge to 8.5 points.
SAME_TEAM_FUDGE: dict[frozenset[str], float] = {
    frozenset({"Modus", "OneThree111"}): 0.9,
}


def _apply_fudge(win_pct: float, team1: Iterable[str], team2: Iterable[str]) -> float:
    s1, s2 = frozenset(team1), frozenset(team2)
    for pair, scale in SAME_TEAM_FUDGE.items():
        if pair <= s1 or pair <= s2:
            win_pct = 0.5 + (win_pct - 0.5) * scale
    return win_pct


def rate_roster(
    roster: Iterable[str], computed: RatingsAndCounts
) -> dict[str, PlackettLuceRating]:
    """One openskill rating per name on the roster - nobody is ever left out.

    Both callers used to build their teams as ``[ratings[p] for p in team if p
    in ratings]`` over ``compute_player_ratings(...).ratings``, which is filtered
    to players with more than ``MIN_GAMES`` games. A newcomer was therefore
    *deleted from the team*, and ``predict_win`` - which sums each side's mu -
    was asked to compare a 2-man side against a 3-man one. The side holding the
    newcomer read ~25 mu short, so the balancer stacked it to compensate: on a
    six-man roster containing a 36-game player, every split came back 0.75-1.00
    and the "fairest" one paired the newcomer with the two strongest players in
    the group. `RatingsAndCounts.rating_for` is what makes a hole impossible.

    Built once per roster rather than per split: a `PlackettLuceRating` mints a
    uuid4 on construction, and the partition path rates the same dozen players
    for every one of thousands of partitions.
    """
    model = get_model()
    return {name: computed.rating_for(name).to_rating(model) for name in roster}


@derived(on=CORPUS, maxsize=128)
def balance_teams(
    games: list[MatchInfo], player_list: frozenset[str]
) -> dict[tuple[str, ...], float]:
    """Win probability for every way of splitting `player_list` into two teams.

    This used to key on `player_list` alone behind a 12h TTL, which meant it
    silently answered from ratings up to half a day stale. That conflated two
    different things: *deriving* the numbers, and *holding* an answer steady for
    a game night. Deriving them is this function's job and it now tracks the
    corpus like every other derivation. The hold is a product decision and lives
    where it is visible - `routes/players.balance_teams`, six hours per roster.
    """
    model = get_model()
    # Sorted, and de-duplicated after resolution. Sorted because the team tuples
    # below take their element order from this list, and iterating the frozenset
    # directly made that order depend on PYTHONHASHSEED - so the same roster came
    # back as "Skip,Syn" on one dyno and "Syn,Skip" after a restart. De-duplicated
    # because two aliases for one player ("skp" and "Skip") would otherwise both
    # land here and be treated as two people.
    day_players = sorted({player_ids.resolve_player_name(n) for n in player_list})
    team_size = len(day_players) // 2
    if team_size == 0:
        return {}
    rated = rate_roster(day_players, compute_player_ratings(games))

    team_win_pct = {}
    seen_matchups: set[frozenset[tuple[str, ...]]] = set()
    for team1 in combinations(day_players, team_size):
        team2 = tuple(p for p in day_players if p not in team1)
        # A matchup, not a team: for an even split, `combinations` yields each
        # pairing twice (once from either side). Keying on the team alone only
        # caught that when the same side happened to be stored first.
        matchup = frozenset({team1, team2})
        if matchup in seen_matchups:
            continue
        seen_matchups.add(matchup)

        team1_ratings = [rated[p] for p in team1]
        team2_ratings = [rated[p] for p in team2]
        win1_prop, win2_prop = model.predict_win([team1_ratings, team2_ratings])
        win1_prop = _apply_fudge(win1_prop, team1, team2)
        win2_prop = 1 - win1_prop
        logger.debug(
            "team matchup", team1=team1, team2=team2, win1=win1_prop, win2=win2_prop
        )
        # Exactly one entry per matchup - the favoured side, or team1 when the
        # two are level. Storing every side at >= 0.5 listed both halves of a
        # dead-even matchup as if they were separate options.
        if win1_prop >= win2_prop:
            team_win_pct[tuple(team1)] = win1_prop
        else:
            team_win_pct[tuple(team2)] = win2_prop
    logger.debug("team win probs", count=len(team_win_pct))
    return dict(sorted(team_win_pct.items(), key=lambda x: x[1]))


def partition_into_teams(
    players: list[str], team_size: int
) -> Iterator[list[list[str]]]:
    """
    Generate all possible ways to partition players into teams.

    Args:
        players: List of (name, Rating) tuples
        team_size: Size of each team

    Yields:
        Each possible partition as a list of teams
    """
    n = len(players)
    num_teams = n // team_size

    if n % team_size != 0:
        raise ValueError(f"Cannot divide {n} players into teams of {team_size}")

    def partition_recursive(
        remaining: list[str], current_partition: list[list[str]], teams_formed: int
    ) -> Iterator[list[list[str]]]:
        if teams_formed == num_teams:
            yield current_partition
            return

        # We need to form teams_left teams from players_left players
        # To avoid duplicates, only consider combinations where the first
        # remaining player is in the team
        first_player = remaining[0]

        # Choose team_size-1 more players from the rest
        for team_members in combinations(remaining[1:], team_size - 1):
            team = [first_player, *list(team_members)]
            new_remaining = [p for p in remaining if p not in team]

            yield from partition_recursive(
                new_remaining, [*current_partition, team], teams_formed + 1
            )

    yield from partition_recursive(players, [], 0)


def create_balanced_teams(
    games: list[MatchInfo], player_list: set[str], team_size: int = 2
) -> list[list[str]]:
    resolved_players = [player_ids.resolve_player_name(n) for n in player_list]
    rated = rate_roster(resolved_players, compute_player_ratings(games))
    team_configs = dict(enumerate(partition_into_teams(resolved_players, team_size)))

    config_rating = {
        config_id: rate_team_partition(team_config, rated)
        for config_id, team_config in team_configs.items()
    }

    best, _score = min(config_rating.items(), key=lambda x: x[1])

    return team_configs[best]


def rate_team_partition(
    teams: list[list[str]], rated: Mapping[str, PlackettLuceRating]
) -> float:
    """How unbalanced this partition is - 0.0 is perfectly even.

    `rated` must cover every name in `teams`; build it with `rate_roster`, which
    is what guarantees that.
    """
    model = get_model()
    loss = 0.0
    for matchup in combinations(teams, 2):
        team1, team2 = matchup
        ratings1 = [rated[p] for p in team1]
        ratings2 = [rated[p] for p in team2]
        win1_prob, _win2_prob = model.predict_win([ratings1, ratings2])
        win1_prob = _apply_fudge(win1_prob, team1, team2)
        loss += (0.5 - win1_prob) ** 2
    return loss
