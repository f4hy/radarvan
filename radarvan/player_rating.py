"""Player skill ratings - computes OpenSkill (Plackett-Luce) ratings from match history,
tracking per-day/per-match rating changes and upsets."""

# Needed so self-references (e.g. NamedRating.with_min_sigma's own return type)
# resolve under Python < 3.14, which evaluates annotations eagerly unless deferred
# like this. 3.14+ defers by default (PEP 649) so this is a no-op there - required
# for the ml/ 3.13 training venv (see pyproject.toml's ml group).
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import NamedTuple
from openskill.models import PlackettLuce, PlackettLuceRating
from collections import Counter, defaultdict
from . import player_ids
from . import game_composition
from .derived import CORPUS, derived
from radarvan.api_types import (
    MatchInfo,
)
from datetime import date
import structlog

logger = structlog.get_logger(__name__)


NON_COMPETITIVE: set[str] = {"EasyArmy", "MediumArmy"}

MIN_GAMES = 45
ITERATIONS = 3

# The floor every pass applies to sigma before re-rating (see _reseed).
MIN_SIGMA = 5.0

# How far below the weakest established player a newcomer is assumed to sit.
# One beta - the model's own per-player performance noise - rather than a number
# read off today's leaderboard, so it stays meaningful as the scale drifts.
NEW_PLAYER_MARGIN_BETAS = 1.0

# ...and with this multiple of the usual starting uncertainty, because "we have
# not seen you play" is a wider claim than "you are weak".
NEW_PLAYER_SIGMA_SCALE = 2.0

# When a game has any CPU player, scale down how far each player's rating moves
# (both mu and sigma). 1.0 = full movement, 0.0 = no movement. CPU games still
# count, just with diminished weight.
CPU_GAME_RATING_SCALE = 0.1


# Guests whose rating is asserted rather than learned, as a multiple of the top
# established human's ordinal.
#
# Excal and Dominator are (semi-)pro players who have played with the group a
# handful of times. Their games rate like anyone else's, but a handful of games
# can never *move* a rating far, by design: `_reseed` shrinks a sub-MIN_GAMES
# player back toward the newcomer prior on every pass, which is exactly what
# stops a short hot streak from minting a top-of-the-board rating. That
# safeguard is right for a stranger and wrong for someone already known to
# outclass the whole group, so these two are stated instead of inferred.
#
# Stated here rather than by injecting fabricated wins. A match is a row in the
# one corpus that W/L records, head-to-head, superlatives, the game-night recap
# and the duration histogram all read, so buying a rating with fake games would
# pay for it in fictional games surfacing on six other pages - and it would take
# a great many of them, since `_reseed` pulls the mu back every pass until the
# game count clears MIN_GAMES.
#
# A *multiple of the leader*, not a fixed mu, for the same reason
# `_newcomer_prior` is relative: openskill has no absolute anchor, this corpus
# has already drifted, and a constant would quietly mean something different in
# six months. Delete an entry to hand the player back to the model.
GUEST_RATING_MULTIPLIERS: dict[str, float] = {
    "Excal": 2.0,
    "Domi": 1.5,
}

# Asserted, so asserted confidently: the same floor every converged rating
# lands on. A wide sigma would undo the point - `predict_win` divides the mu
# gap by the two teams' pooled uncertainty, so an unsure 2x rating reads as a
# *smaller* edge than a sure 1.5x one.
GUEST_SIGMA = MIN_SIGMA


@dataclass(slots=True)
class NamedRating:
    """Wrapper around PlackettLuceRating where name is guaranteed to be str."""

    name: str
    mu: float
    sigma: float
    at_date: date | None = None

    def ordinal(self) -> float:
        return self.mu - 3 * self.sigma

    def with_min_sigma(self, min_sigma: float) -> NamedRating:
        return NamedRating(
            name=self.name,
            mu=self.mu,
            sigma=max(self.sigma, min_sigma),
            at_date=self.at_date,
        )

    def to_rating(self, model: PlackettLuce) -> PlackettLuceRating:
        return model.rating(name=self.name, mu=self.mu, sigma=self.sigma)


def initialize_player(name: str, model: PlackettLuce) -> NamedRating:
    r = model.rating(name=name)
    known_players = player_ids.HUMAN_NAMES
    if name in NON_COMPETITIVE:
        return NamedRating(name=name, mu=0.5, sigma=r.sigma / 2.0)
    if player_ids.is_cpu_name(name):
        return NamedRating(name=name, mu=r.mu, sigma=r.sigma / 2.0)
    if name in known_players:
        return NamedRating(name=name, mu=r.mu, sigma=r.sigma)
    return NamedRating(name=name, mu=r.mu, sigma=r.sigma * 8)


@lru_cache(maxsize=1)
def get_model() -> PlackettLuce:
    # A nullary constant, not a derivation: nothing versions it and nothing
    # invalidates it. lru_cache(1) rather than the registry, which would add a
    # dependency token and a lock to a call that has neither.
    # return PlackettLuce(beta=(25.0/3.0), tau=(25.0 / 200.0))
    return PlackettLuce(beta=(25.0 / 4.0))


@dataclass(slots=True)
class RatingDailyChange:
    date: date
    delta: float


@dataclass(slots=True)
class RatingMatchChange:
    match_id: int
    delta: float
    at_date: date


# Per-player performance noise for *displayed* win probabilities only. This is
# deliberately NOT the beta in get_model(): that one drives rate(), and moving it
# would move every rating in the app. See displayed_win_probs.
#
# Fitted by maximum likelihood over the whole rating corpus (2026-08-28): 7.8,
# against get_model()'s 6.25. The fit is flat - 5.9 and 11.7 cost 0.006 log-loss
# either side of it - and stable as history grows (6.9-7.8 over expanding
# prefixes), so it is a constant rather than something refit at runtime.
DISPLAY_BETA = 7.8


def displayed_win_probs(
    teams: list[list[PlackettLuceRating]], beta: float = DISPLAY_BETA
) -> list[float]:
    """Calibrated P(win) per team, for probabilities we actually show people.

    ``PlackettLuce.predict_win`` is badly overconfident here, and the reason is
    structural rather than a bad beta. Its two-team branch is

        Phi( (mu_A - mu_B) / sqrt(2*beta^2 + sigma_A^2 + sigma_B^2) )

    where ``mu_A`` is the *sum* of the team's mus. The numerator therefore grows
    with team size while the dominant ``2*beta^2`` term does not - one beta per
    team however many people are on it. Measured as-of over 812 games, the
    favourite it names wins:

        1v1  stated 0.81  actual 0.75
        2v2  stated 0.79  actual 0.66
        3v3  stated 0.73  actual 0.57
        4v4  stated 0.71  actual 0.49   <- its most confident format is a coin flip

    (4v4 really is near-unpredictable: openskill scores AUC 0.529 there and a
    17-parameter Bradley-Terry fit gets 0.519, so the right answer for most 4v4s
    is "about even" - which the library formula is structurally unable to say.)

    The fix is to let the team's performance noise scale with the team, i.e.
    ``beta^2 * (n_A^2 + n_B^2)`` in place of ``2*beta^2``. That is the same
    correction ``ml.config.ModelConfig.size_norm`` applies to the neural model.
    It takes pooled log-loss from 0.806 - worse than a coin flip - to 0.659, and
    it is the only variant that calibrates every format at once: a flat
    temperature fixes the average and still overstates 4v4 while understating
    1v1. Full write-up in ``ml/model_design.md``.

    Monotone in ``mu_A - mu_B``, so **which** team is favoured is unchanged;
    only the stated confidence moves (and, across formats, the ordering of how
    surprising two upsets were - correctly, since a 4v4 gap means less).

    Two teams only, which is all ``build_teams`` ever produces.
    """
    if len(teams) != 2:
        raise ValueError(f"expected exactly 2 teams, got {len(teams)}")

    def summed(team: list[PlackettLuceRating]) -> tuple[float, float, int]:
        return (
            sum(r.mu for r in team),
            sum(r.sigma**2 for r in team),
            len(team),
        )

    (mu_a, var_a, n_a), (mu_b, var_b, n_b) = (summed(t) for t in teams)
    spread = math.sqrt(beta**2 * (n_a**2 + n_b**2) + var_a + var_b)
    p_a = 0.5 * (1.0 + math.erf((mu_a - mu_b) / (spread * math.sqrt(2.0))))
    return [p_a, 1.0 - p_a]


@dataclass(slots=True)
class GameUpset:
    """A game where the team the model favored to win lost.

    Which team was favored comes from the model's pre-game ``predict_win``,
    using the (converged) ratings from the final rating pass. The **probability**
    is ``displayed_win_probs`` on the same ratings - ``predict_win``'s own number
    is not calibrated and is not fit to show anyone. Both agree on who was
    favored, so this changes what the card says, never which game it picks.
    """

    match_id: int
    at_date: date
    favored_team: int
    favored_win_prob: float
    favored_players: list[str]
    winning_team: int
    winner_win_prob: float
    winner_players: list[str]

    @property
    def surprise(self) -> float:
        """How lopsided the upset was: favorite's edge over the actual winner."""
        return self.favored_win_prob - self.winner_win_prob


def _leaderboard(
    ratings: dict[str, NamedRating], game_counts: dict[str, int]
) -> list[NamedRating]:
    """Players over MIN_GAMES, best first. The one spelling of the display cut -
    `compute_player_ratings` logs it once per pass and reports it as
    `RatingsAndCounts.ratings`."""
    return sorted(
        (
            r
            for r in ratings.values()
            if include_rating(game_counts, r.name, min_game_count=MIN_GAMES)
        ),
        key=lambda r: r.ordinal(),
        reverse=True,
    )


@dataclass(slots=True)
class RatingsAndCounts:
    # Every seeded player, including those under MIN_GAMES, and the rating to
    # assume for anyone not seeded at all. Ask through `rating_for`: a caller
    # that reasons about a player - team balance, prediction - must never end up
    # holding a hole, because dropping a player is not a small error. It asks
    # predict_win to compare a 2-man side to a 3-man one.
    all_ratings: dict[str, NamedRating]
    newcomer_prior: NamedRating
    game_counts: dict[str, int]
    over_time: dict[str, list[NamedRating]]
    daily_changes: dict[str, list[RatingDailyChange]]
    match_changes: dict[str, list[RatingMatchChange]]
    ordinal_high: dict[str, float]
    ordinal_low: dict[str, float]
    upsets: list[GameUpset]

    @property
    def ratings(self) -> list[NamedRating]:
        """The leaderboard: best first, and only players over MIN_GAMES.

        Derived rather than stored, so it cannot drift from `all_ratings`. A
        rating with ten games behind it is not worth *showing* - which is all
        this filter is for. Anything that reasons about a player wants
        `rating_for`, and `queries/players.player_ratings_payload` builds the
        wire payload from here.
        """
        return _leaderboard(self.all_ratings, self.game_counts)

    def rating_for(self, name: str) -> NamedRating:
        """This player's rating - never None, never a hole in a team.

        Callers used to build their own `{r.name: r for r in .ratings}`, which
        is the MIN_GAMES-gated view, and then paper over the misses: create_teams
        dropped the player outright, ml/predict substituted openskill's mu=25
        default. Both threw away a real computed rating. One accessor that
        cannot be combined incorrectly replaces both.
        """
        return self.all_ratings.get(name) or replace(self.newcomer_prior, name=name)


class TeamBuildResult(NamedTuple):
    teams: dict[int, list[str]]
    counts: dict[str, int]


class RatingUpdateResult(NamedTuple):
    updated: dict[str, NamedRating]
    history: dict[str, NamedRating]
    upset: GameUpset | None


class ProcessGamesResult(NamedTuple):
    players: dict[str, NamedRating]
    rating_over_time: dict[str, list[NamedRating]]
    match_changes: dict[str, list[RatingMatchChange]]
    upsets: list[GameUpset]


def _collect_all_players(games: list[MatchInfo]) -> set[str]:
    """Everyone who needs a starting rating: the competitors, not the lobby.

    ``build_teams`` looks up participants, a subset of these - seeding the
    whole competitor set costs nothing and keeps this in step with
    ``filter_for_rating``, which judges the same slots. Seeding a *spectator*
    did buy something wrong: a rating entry for someone who never played.
    """
    return {name for game in games for name in game.roster().competitor_names()}


def build_teams(game: MatchInfo) -> TeamBuildResult | None:
    """Return (teams, counts_increment) or None if game should be skipped."""
    teams: dict[int, list[str]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    actual_players = game.roster().participants
    logger.debug("processing game", game_id=game.id, players=game.players)
    for player in actual_players:
        name = player_ids.resolve_player_name(player.name, player.color)
        teams[player.team].append(name)
        counts[name] += 1
    if len(teams) != 2:
        return None
    return TeamBuildResult(teams=teams, counts=counts)


def _compute_surprise_uncertainty(
    score_values: list[float], prediction: list[float]
) -> float:
    surprize = 1.0 - sum(b * p for b, p in zip(score_values, prediction, strict=True))
    logger.debug(
        "surprise", scores=score_values, prediction=prediction, surprise=surprize
    )
    return (surprize - 0.5) * 0.1 if surprize > 0.85 else 0.0


def _update_ratings_for_game(
    game: MatchInfo,
    teams: dict[int, list[str]],
    players: dict[str, NamedRating],
    model: PlackettLuce,
) -> RatingUpdateResult:
    """Return (updated_player_ratings, new_history_entries)."""
    team_ids = list(teams.keys())
    scores = {t: 1.0 if game.winning_team == t else 0 for t in team_ids}
    score_values = list(scores.values())
    pteams = [[players[p].to_rating(model) for p in team] for team in teams.values()]
    prediction = model.predict_win(teams=pteams)
    surprize_uncertainty_add = _compute_surprise_uncertainty(score_values, prediction)
    logger.debug("rating game", teams=teams, uncertainty_add=surprize_uncertainty_add)
    new_ratings = model.rate(teams=pteams, scores=score_values)
    has_cpu = game.roster().has_cpu
    # CPU games are noise as "upsets" (the rating model down-weights them); skip them.
    upset = (
        None
        if has_cpu
        # Not `prediction`: that is predict_win's uncalibrated number, which is
        # right for _compute_surprise_uncertainty (a threshold on the rating
        # path) and wrong to print. See displayed_win_probs.
        else _detect_upset(
            game, teams, dict(zip(team_ids, displayed_win_probs(pteams), strict=True))
        )
    )
    scale = CPU_GAME_RATING_SCALE if has_cpu else 1.0
    updated: dict[str, NamedRating] = {}
    history: dict[str, NamedRating] = {}
    for t in new_ratings:
        for p in t:
            if p.name is None:
                continue
            prev = players[p.name]
            target_sigma = p.sigma + surprize_uncertainty_add
            new_rate = NamedRating(
                name=p.name,
                mu=prev.mu + scale * (p.mu - prev.mu),
                sigma=prev.sigma + scale * (target_sigma - prev.sigma),
                at_date=game.date,
            )
            updated[p.name] = new_rate
            history[p.name] = new_rate
    return RatingUpdateResult(updated=updated, history=history, upset=upset)


def _detect_upset(
    game: MatchInfo,
    teams: dict[int, list[str]],
    win_prob_by_team: dict[int, float],
) -> GameUpset | None:
    """Return a GameUpset if the model's favored team lost, else None."""
    favored_team = max(win_prob_by_team, key=lambda t: win_prob_by_team[t])
    if favored_team == game.winning_team:
        return None
    return GameUpset(
        match_id=game.id,
        at_date=game.date,
        favored_team=favored_team,
        favored_win_prob=win_prob_by_team[favored_team],
        favored_players=list(teams[favored_team]),
        winning_team=game.winning_team,
        winner_win_prob=win_prob_by_team.get(game.winning_team, 0.0),
        winner_players=list(teams.get(game.winning_team, [])),
    )


class _RatableGame(NamedTuple):
    """A game that passed the rating gate, with its teams already resolved.

    ``compute_player_ratings`` runs ITERATIONS passes over the same games, and
    neither the gate nor ``build_teams`` depends on the current ratings - both
    resolve every competitor's alias, so redoing them per pass tripled the
    name-resolution work for no change in result.
    """

    game: MatchInfo
    teams: dict[int, list[str]]


class _PreparedCorpus(NamedTuple):
    """The games the passes iterate, and how much we know about each player.

    The counts are summed here rather than carried per game: they are a property
    of the corpus, not of a pass, and `_process_games` ran over all ITERATIONS
    of them re-adding the same numbers. Keeping them on `_RatableGame` also held
    a small dict per game alive for the whole computation for one use.
    """

    games: list[_RatableGame]
    counts: dict[str, int]


def _ratable_games(games: list[MatchInfo]) -> _PreparedCorpus:
    """Gate + team-build every game once, in chronological order."""
    prepared: list[_RatableGame] = []
    counts: Counter[str] = Counter()
    for game in sorted(games, key=lambda x: x.timestamp):
        if not is_ratable_team_game(game):
            continue
        result = build_teams(game)
        if result is None:
            continue
        prepared.append(_RatableGame(game=game, teams=result.teams))
        counts.update(result.counts)
    return _PreparedCorpus(games=prepared, counts=dict(counts))


def _process_games(
    games: list[_RatableGame],
    initial_players: dict[str, NamedRating],
    model: PlackettLuce,
) -> ProcessGamesResult:
    players = dict(initial_players)
    rating_over_time: dict[str, list[NamedRating]] = {name: [] for name in players}
    match_changes: dict[str, list[RatingMatchChange]] = {name: [] for name in players}
    upsets: list[GameUpset] = []
    for game, teams in games:
        pre_ordinals = {
            name: players[name].ordinal() for team in teams.values() for name in team
        }
        updated, history, upset = _update_ratings_for_game(game, teams, players, model)
        players.update(updated)
        if upset is not None:
            upsets.append(upset)
        for name, entry in history.items():
            rating_over_time[name].append(entry)
            match_changes[name].append(
                RatingMatchChange(
                    match_id=game.id,
                    delta=entry.ordinal() - pre_ordinals[name],
                    at_date=game.date,
                )
            )
    return ProcessGamesResult(
        players=players,
        rating_over_time=rating_over_time,
        match_changes=match_changes,
        upsets=upsets,
    )


def _newcomer_prior(
    ratings: dict[str, NamedRating], counts: dict[str, int], model: PlackettLuce
) -> NamedRating:
    """What we assume about someone we have barely seen play.

    Deliberately *relative* to the players we do know. openskill has no absolute
    anchor - the whole scale is free to drift, and this corpus has drifted to a
    mu range of roughly 10..38, so the library's own default of mu=25 seeds a
    brand-new player above two thirds of the regulars. (Lowering the default for
    everyone fixes nothing: measured, it shifts every mu down by the same amount
    and leaves the ordering identical.) Anchoring one beta below the weakest
    established player says the thing we actually mean - "assume they are the
    weakest here until they show otherwise" - and keeps saying it as the scale
    moves.

    On the first pass nobody is established yet, and then the margin is dropped
    along with the anchor: with every player still sitting on the same default
    there is nothing to be weaker *than*, and subtracting a beta from the shared
    starting point would single the newcomer out on no evidence at all.
    """
    established = [
        r.mu
        for name, r in ratings.items()
        # `include_rating` is the app's definition of "enough games to have a
        # rating worth quoting"; reuse it rather than spelling the threshold a
        # second time. Its CPU exemption is not wanted here - HardArmy is not a
        # regular, and its rating is seeded differently.
        if not player_ids.is_cpu_name(name)
        and include_rating(counts, name, min_game_count=MIN_GAMES)
    ]
    mu = (
        min(established) - NEW_PLAYER_MARGIN_BETAS * model.beta
        if established
        else model.mu
    )
    # The wide sigma stands either way: "we have not seen you play" is true on
    # the first pass too.
    return NamedRating(name="", mu=mu, sigma=model.sigma * NEW_PLAYER_SIGMA_SCALE)


def _apply_guest_ratings(
    ratings: dict[str, NamedRating], counts: dict[str, int]
) -> dict[str, NamedRating]:
    """Replace each guest's learned rating with its asserted multiple of the
    leader's ordinal. Returns a new dict; the input is left alone.

    Runs as the last step of ``compute_player_ratings``, after the passes and
    after ``_newcomer_prior``. The passes must see the guests' *real* ratings:
    rating the group's games against an asserted 2x opponent would mean losing
    to Excal barely dents anyone and beating him is worth a fortune, which is a
    much bigger lie than the one being told here.

    The anchor skips CPUs (HardArmy sits mid-board and is seeded on a different
    scale, exactly as ``_newcomer_prior`` reasons) and skips the guests
    themselves. ``_leaderboard`` already drops both - CPUs never top it, guests
    are under MIN_GAMES - but a guest who did cross the line would otherwise be
    anchored to their own boosted rating and compound it on every recomputation.

    A guest with no games at all still gets an entry, so ``rating_for`` answers
    for them the first time they are picked on the Balance Teams page.
    """
    board = [
        r
        for r in _leaderboard(ratings, counts)
        if not player_ids.is_cpu_name(r.name) and r.name not in GUEST_RATING_MULTIPLIERS
    ]
    if not board:
        return ratings
    top_ordinal = board[0].ordinal()
    boosted = dict(ratings)
    for name, multiplier in GUEST_RATING_MULTIPLIERS.items():
        existing = ratings.get(name)
        boosted[name] = NamedRating(
            name=name,
            # ordinal() is mu - 3*sigma, solved for the mu that lands the
            # ordinal on the multiple asked for.
            mu=multiplier * top_ordinal + 3 * GUEST_SIGMA,
            sigma=GUEST_SIGMA,
            at_date=existing.at_date if existing else None,
        )
    return boosted


def _reseed(
    ratings: dict[str, NamedRating], counts: dict[str, int], model: PlackettLuce
) -> dict[str, NamedRating]:
    """Starting ratings for the next pass: shrink the barely-seen back toward
    the newcomer prior, then floor sigma.

    This has to run every pass, not once before the first. ``compute_player_ratings``
    seeds from ``initialize_player`` and then feeds each pass the *previous
    pass's* output, so a starting prior only ever constrains pass 1 and is
    swamped by passes 2 and 3 replaying the same games. Measured on the live
    corpus, seeding a 36-game newcomer 25 mu lower moved them from 8th to 13th
    after one pass and left them 5th after three - i.e. the prior alone is
    almost inert at the shipped ITERATIONS. Re-applying it here is what makes it
    bite.

    The weight ramps linearly to 1.0 at MIN_GAMES and stays there, so a player
    with enough games keeps exactly their own rating (this reduces to the plain
    sigma floor it replaced) and nobody's rating steps the night they cross the
    line. CPUs are exempt: they get their own seed in ``initialize_player`` and
    are not newcomers whatever their game count.

    Only mu is pulled back. Sigma is left to converge on its own (floored, as
    before), because in openskill sigma *is* the learning rate: re-inflating a
    newcomer's uncertainty every pass would pin them at maximum volatility and
    let a short winning run carry them further than the evidence does - the
    opposite of what holding them near the prior is for. The wide sigma belongs
    to the seed, where it says "we have not seen you play"; once we have seen
    them, their own sigma is the better answer.
    """
    prior = _newcomer_prior(ratings, counts, model)
    reseeded: dict[str, NamedRating] = {}
    for name, rating in ratings.items():
        # How much of this player's own record we believe, ramped linearly to
        # full trust at MIN_GAMES ratable games; the rest of the weight goes to
        # the prior. Continuous by construction, so nobody's rating jumps the
        # night they cross the line, and at trust 1.0 this is exactly the sigma
        # floor it replaced - which is why a CPU (seeded by `initialize_player`,
        # never a newcomer) can take the same branch by being trusted outright.
        exempt = player_ids.is_cpu_name(name) or name in NON_COMPETITIVE
        trust = 1.0 if exempt else min(1.0, counts.get(name, 0) / MIN_GAMES)
        reseeded[name] = replace(
            rating.with_min_sigma(MIN_SIGMA),
            mu=trust * rating.mu + (1.0 - trust) * prior.mu,
        )
    return reseeded


def _log_sorted_ratings(
    sorted_ratings: list[NamedRating], game_counts: dict[str, int]
) -> None:
    for rating in sorted_ratings:
        logger.debug(
            "rating",
            name=rating.name,
            games=game_counts.get(rating.name),
            ordinal=round(rating.ordinal(), 1),
            mu=round(rating.mu, 1),
            sigma=round(rating.sigma, 1),
        )


def include_rating(game_counts: dict[str, int], name: str, min_game_count: int) -> bool:
    if player_ids.is_cpu_name(name):
        return True
    return game_counts.get(name, 0) > min_game_count


def filter_for_rating(game: MatchInfo) -> bool:
    if game.winning_team < 1:
        return False
    # Disconnects/desyncs/quit-early/too-short games aren't real results.
    if game.incomplete:
        return False
    if game.composition is None:
        return False
    if game.composition.is_comp_stomp:
        return False
    if game.composition.is_ffa:
        return False
    if not game.composition.is_balanced:
        return False
    # Who *played*, never who watched. Whether a game is ratable is a property
    # of the game, so adding or removing a spectator must not change the
    # answer - bracket 1v1s are streamed from accounts named after the matchup
    # ("Gorn.v.131"), which are in nobody's roster, and reading every slot here
    # made 23 otherwise-competitive games unratable.
    names = game.roster().competitor_names()
    if names & NON_COMPETITIVE:
        return False
    return names <= player_ids.PLAYER_NAMES


def is_tournament_1v1(game: MatchInfo) -> bool:
    """A 1v1 that counted toward a tournament.

    The one kind of 1v1 that moves ratings. A tournament link is only ever
    written by ``tournament_membership.sync_links`` (scheduled bracket slot,
    right two players, right game night) or by an admin, so it can't be earned
    by a practice game - which is what the rest of the 1v1s are.
    """
    comp = game.composition
    if comp is None or not comp.is_1v1:
        return False
    if game.tournament is None:
        return False
    return game_composition.competitive_game_filter(comp) and filter_for_rating(game)


def is_ratable_team_game(game: MatchInfo) -> bool:
    """True for a competitive, balanced two-team game eligible for rating.

    Single source of truth for "should this game move ratings / count for synergy",
    shared by the rating pass and the synergy model.

    1v1s are delegated to ``is_tournament_1v1`` rather than re-tested here, so
    there is one definition of "a 1v1 that counts" for the gate, the manifest
    counter, and the docs to share. A bracket game is a real result between two
    people and belongs in their ratings; a casual 1v1 usually isn't - people
    play them to drill a matchup or try an off-meta build - and they're wildly
    concentrated, one pair accounting for over half of them, so letting them in
    would rate that rivalry rather than the ladder.

    Ordered cheapest-first: the composition checks are attribute reads, while
    ``filter_for_rating`` resolves every competitor's name.
    """
    comp = game.composition
    if comp is None:
        return False
    if comp.is_1v1:
        return is_tournament_1v1(game)
    if not game_composition.competitive_game_filter(comp):
        return False
    return filter_for_rating(game)


@derived(on=CORPUS, maxsize=6)
def compute_player_ratings(games: list[MatchInfo]) -> RatingsAndCounts:
    """Ratings over the supplied games.

    Keyed on the ids in `games` *and* the corpus epoch. The ids alone would be
    wrong: a reparse or a WinnerOverride changes a match's winner while leaving
    its id untouched, so `competitive_matches` would hand this a corrected list
    and get the pre-correction ratings back. See derived/versions.py.
    """
    model = get_model()
    filtered_games = [g for g in games if filter_for_rating(g)]
    all_players = _collect_all_players(filtered_games)
    player_ratings = {name: initialize_player(name, model) for name in all_players}

    # Gate + resolve teams once, then reuse across every pass (see _RatableGame).
    # Before the first pass, not between the seeding and the loop: `_reseed`
    # needs the per-player game counts to know who is still a newcomer.
    prepared, ratable_counts = _ratable_games(filtered_games)
    game_counts = dict.fromkeys(all_players, 0) | ratable_counts
    logger.debug("initial players", players=player_ratings)

    for i in range(ITERATIONS):
        player_ratings, rating_over_time, match_changes, upsets = _process_games(
            prepared, _reseed(player_ratings, game_counts, model), model
        )
        logger.debug("pass", iteration=i)
        _log_sorted_ratings(_leaderboard(player_ratings, game_counts), game_counts)
    logger.debug("done computing ratings")

    over_time_filtered = {n: v for n, v in rating_over_time.items() if len(v) > 30}

    ordinal_high = {
        name: max(r.ordinal() for r in entries)
        for name, entries in rating_over_time.items()
        if entries
    }
    ordinal_low = {
        name: min(r.ordinal() for r in entries)
        for name, entries in rating_over_time.items()
        if entries
    }

    daily_changes: dict[str, list[RatingDailyChange]] = {}
    for name, changes in match_changes.items():
        by_date: dict[date, float] = defaultdict(float)
        for mc in changes:
            by_date[mc.at_date] += mc.delta
        daily_changes[name] = [
            RatingDailyChange(date=d, delta=delta)
            for d, delta in sorted(by_date.items())
        ]

    sorted_upsets = sorted(upsets, key=lambda u: u.surprise, reverse=True)

    # The prior first, off the learned ratings, then the guest overrides on top.
    # Both read the leaderboard, and the order is what keeps the assertion from
    # feeding back: a boosted guest must not be able to shift what "the weakest
    # established player" means for everyone we have genuinely not seen play.
    newcomer_prior = _newcomer_prior(player_ratings, game_counts, model)
    player_ratings = _apply_guest_ratings(player_ratings, game_counts)

    return RatingsAndCounts(
        all_ratings=player_ratings,
        # Computed here, where the model and the final ratings are both in hand,
        # rather than re-derived by every caller that needs to place a stranger.
        newcomer_prior=newcomer_prior,
        game_counts=game_counts,
        over_time=over_time_filtered,
        daily_changes=daily_changes,
        match_changes=match_changes,
        ordinal_high=ordinal_high,
        ordinal_low=ordinal_low,
        upsets=sorted_upsets,
    )
