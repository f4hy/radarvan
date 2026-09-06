"""Player skill ratings - computes OpenSkill (Plackett-Luce) ratings from match history,
tracking per-day/per-match rating changes and upsets."""

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

# Static and low - what we assume about someone we've barely seen play. See
# CLAUDE.md's rating section for why this and GUEST_INITIAL_MU are both flat
# constants rather than computed.
NEWCOMER_PRIOR_MU = 3.0
NEWCOMER_PRIOR_SIGMA = 16.0  # wide: "never seen you play" is a broad claim

# When a game has any CPU player, scale down how far each player's rating moves
# (both mu and sigma). 1.0 = full movement, 0.0 = no movement. CPU games still
# count, just with diminished weight.
CPU_GAME_RATING_SCALE = 0.1


# Excal/Marakar/Domi: (semi-)pro visitors known to outclass the group with too
# few real games to prove it from scratch. Static, deliberately high *starting*
# mu, not a permanent override - real games move it from there like anyone
# else's. Roughly ordered against the corpus's real leaders (high-30s/low-40s
# ordinal currently), not derived from anything. See CLAUDE.md. Delete an
# entry to hand the player back to the model.
GUEST_INITIAL_MU: dict[str, float] = {
    "Excal": 51.0,
    "Marakar": 50.0,
    "Domi": 45.0,
}

# Players who joined the corpus partway through, seeded at an estimate of
# their skill *at the time they entered* (not their current rating) rather
# than the neutral default - same reasoning as GUEST_INITIAL_MU, applied
# retroactively instead of to a stranger.
PLAYER_INITIAL_MU: dict[str, float] = {
    "Modus": 35.0,
    "Gorn": 30.0,
    "OneThree111": 24.0,
    "Syn": 10.0,
    "STM": 10.0,
    "EnragedFerret": -1.5,
}


def is_guest_name(name: str) -> bool:
    return name in GUEST_INITIAL_MU


# A guest's *starting* sigma - tight, so their high seed isn't taxed by wide
# uncertainty before their first real game (ordinal is mu - 3*sigma). Single
# pass now, so nothing ever resets it back to this value once real games move it.
GUEST_SIGMA = 2.5


@dataclass(slots=True)
class NamedRating:
    """Wrapper around PlackettLuceRating where name is guaranteed to be str."""

    name: str
    mu: float
    sigma: float
    at_date: date | None = None

    def ordinal(self) -> float:
        return self.mu - 3 * self.sigma

    def to_rating(self, model: PlackettLuce) -> PlackettLuceRating:
        return model.rating(name=self.name, mu=self.mu, sigma=self.sigma)


def _seeded(name: str, table: dict[str, float], sigma: float) -> NamedRating:
    return NamedRating(name=name, mu=table[name], sigma=sigma)


def initialize_player(name: str, model: PlackettLuce) -> NamedRating:
    r = model.rating(name=name)
    known_players = player_ids.HUMAN_NAMES
    if name in NON_COMPETITIVE:
        return NamedRating(name=name, mu=0.5, sigma=r.sigma / 2.0)
    if player_ids.is_cpu_name(name):
        return NamedRating(name=name, mu=r.mu / 2.0, sigma=r.sigma / 2.0)
    if is_guest_name(name):
        return _seeded(name, GUEST_INITIAL_MU, GUEST_SIGMA)
    if name in PLAYER_INITIAL_MU:
        return _seeded(name, PLAYER_INITIAL_MU, r.sigma)
    if name in known_players:
        return NamedRating(name=name, mu=r.mu, sigma=r.sigma)
    return NamedRating(name=name, mu=r.mu, sigma=r.sigma * 8)


@lru_cache(maxsize=1)
def get_model() -> PlackettLuce:
    # A nullary constant, not a derivation: nothing versions or invalidates it,
    # so lru_cache(1) rather than the registry's dependency token + lock.
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

    ``PlackettLuce.predict_win`` is structurally overconfident: its two-team
    branch is ``Phi((mu_A - mu_B) / sqrt(2*beta^2 + sigma_A^2 + sigma_B^2))``,
    where ``mu_A`` is the team's *summed* mu - the numerator grows with team
    size, the dominant ``2*beta^2`` term doesn't. Measured over 812 games, the
    named favourite's actual win rate undershoots its stated one, worsening
    with team size (1v1 0.81 stated/0.75 actual, 2v2 0.79/0.66, 3v3 0.73/0.57,
    4v4 0.71/0.49 - its most confident format is a coin flip; 4v4 genuinely is
    near-unpredictable, openskill AUC 0.529 there).

    Fix: scale the noise term with team size, ``beta^2 * (n_A^2 + n_B^2)`` in
    place of ``2*beta^2`` (same correction as ``ml.config.ModelConfig.size_norm``
    on the neural model). Takes pooled log-loss from 0.806 to 0.659 and is the
    only variant that calibrates every format at once - a flat temperature
    fixes the average but still overstates 4v4 while understating 1v1. Full
    write-up in ``ml/model_design.md``.

    Monotone in ``mu_A - mu_B``, so which team is favoured is unchanged - only
    the stated confidence moves. Two teams only, all ``build_teams`` produces.
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
    """Players over MIN_GAMES, best first, plus the guests regardless of games
    played - their rating is asserted, not earned, so the "not enough games to
    trust it" reasoning behind the cut doesn't apply to them. The one spelling
    of the display cut - `compute_player_ratings` logs it and reports it as
    `RatingsAndCounts.ratings`."""
    return sorted(
        (
            r
            for r in ratings.values()
            if is_guest_name(r.name)
            or include_rating(game_counts, r.name, min_game_count=MIN_GAMES)
        ),
        key=lambda r: r.ordinal(),
        reverse=True,
    )


@dataclass(slots=True)
class RatingsAndCounts:
    # Every seeded player, including those under MIN_GAMES, plus the rating to
    # assume for anyone not seeded at all. Ask through `rating_for` - a caller
    # reasoning about a player (team balance, prediction) must never hold a
    # hole, or predict_win ends up comparing a 2-man side to a 3-man one.
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
        """The leaderboard: best first, only players over MIN_GAMES.

        Derived rather than stored, so it can't drift from `all_ratings`. A
        rating with ten games behind it isn't worth *showing*, which is all
        this filter is for - reasoning about a player wants `rating_for`.
        `queries/players.player_ratings_payload` builds the wire payload from
        here.
        """
        return _leaderboard(self.all_ratings, self.game_counts)

    def rating_for(self, name: str) -> NamedRating:
        """This player's rating - never None, never a hole in a team.

        Callers used to build `{r.name: r for r in .ratings}` (the MIN_GAMES-
        gated view) and paper over the misses: create_teams dropped the player
        outright, ml/predict substituted openskill's mu=25 default. One
        accessor replaces both.
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
    whole competitor set costs nothing and stays in step with
    ``filter_for_rating``, which judges the same slots. Seeding a spectator
    would buy a rating entry for someone who never played.
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

    Neither the gate nor ``build_teams`` depends on the current ratings, so
    resolving every competitor's alias once here (rather than inline in
    ``_process_games``) keeps that concern separate from applying ratings.
    """

    game: MatchInfo
    teams: dict[int, list[str]]


class _PreparedCorpus(NamedTuple):
    """The games to rate, and how much we know about each player.

    The counts are summed here rather than carried per game: they are a
    property of the corpus, not of any one game. Keeping them on
    `_RatableGame` instead would hold a small dict per game alive for the
    whole computation for one use.
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


NEWCOMER_PRIOR = NamedRating(name="", mu=NEWCOMER_PRIOR_MU, sigma=NEWCOMER_PRIOR_SIGMA)


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

    Single source of truth for "should this game move ratings / count for
    synergy", shared by the rating pass and the synergy model. 1v1s delegate to
    ``is_tournament_1v1`` rather than being re-tested here, so there's one
    definition everywhere. Casual 1v1s are excluded: they're wildly
    concentrated (one pair is over half of them), so rating them would rate
    that rivalry rather than the ladder - a bracket game is a real result and
    belongs in ratings.

    Ordered cheapest-first: composition checks are attribute reads,
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

    A single chronological pass - see CLAUDE.md's rating section for why the
    old multi-pass/reseed design was dropped in favor of this.

    Keyed on the ids in `games` *and* the corpus epoch. The ids alone would be
    wrong: a reparse or a WinnerOverride changes a match's winner while leaving
    its id untouched, so `competitive_matches` would hand this a corrected list
    and get the pre-correction ratings back. See derived/versions.py.
    """
    model = get_model()
    filtered_games = [g for g in games if filter_for_rating(g)]
    # Guests are seeded (see `initialize_player`) regardless of whether
    # they've played - a guest with no games yet still needs an entry, so
    # `rating_for` answers the first time they're picked on the Balance Teams
    # page, before their first real game ever lands.
    all_players = _collect_all_players(filtered_games) | GUEST_INITIAL_MU.keys()
    player_ratings = {name: initialize_player(name, model) for name in all_players}

    prepared, ratable_counts = _ratable_games(filtered_games)
    game_counts = dict.fromkeys(all_players, 0) | ratable_counts
    logger.debug("initial players", players=player_ratings)

    player_ratings, rating_over_time, match_changes, upsets = _process_games(
        prepared, player_ratings, model
    )
    logger.debug("done computing ratings")
    _log_sorted_ratings(_leaderboard(player_ratings, game_counts), game_counts)

    # Guests are exempted from over_time's "enough games to be worth a
    # sparkline" cut for the same reason they're exempted from MIN_GAMES on
    # the leaderboard: the point of asserting a starting rating is to see it
    # move, however few real games back it so far.
    over_time_filtered = {
        n: v for n, v in rating_over_time.items() if len(v) > 30 or is_guest_name(n)
    }

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

    return RatingsAndCounts(
        all_ratings=player_ratings,
        newcomer_prior=NEWCOMER_PRIOR,
        game_counts=game_counts,
        over_time=over_time_filtered,
        daily_changes=daily_changes,
        match_changes=match_changes,
        ordinal_high=ordinal_high,
        ordinal_low=ordinal_low,
        upsets=sorted_upsets,
    )
