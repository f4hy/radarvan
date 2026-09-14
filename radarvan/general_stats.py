"""Compute generals stats."""

from collections import defaultdict

from .api_types import (
    MatchInfo,
    General,
    GeneralMatchupCell,
    GeneralMatchups,
    GeneralStat,
    GeneralStats,
    Statistic,
    SuperlativeData,
    WinLoss,
)
from . import game_composition
from . import player_ids
import structlog

logger = structlog.get_logger(__name__)


# Prefix marking the persisted Statistic rows below as machine-only data for
# get_generals_stats, not a leaderboard entry - routes/superlatives.py's
# get_superlatives() filters rows with this prefix out of the public feed.
GENERAL_VALUE_STAT_PREFIX = "__general_value_"


def general_value_stats(
    games: list[MatchInfo], details: list[SuperlativeData]
) -> dict[General, tuple[int, int]]:
    """Total value destroyed/lost per general across `games`.

    Joins each match's per-player value totals (`details`, keyed by match_id -
    see superlatives.superlative_data_from_details) back to the general that
    player piloted in that match (`games`). Both lists are expected to cover
    the same match set; details for matches missing from `games` (or vice
    versa) are silently skipped. Scans every match's SuperlativeData, so this
    is only cheap enough to run as part of the nightly superlatives recompute,
    not live per-request - see computed_stats.recompute.
    """
    general_by_match: dict[int, dict[str, General]] = {}
    for g in games:
        general_by_match[g.id] = {
            player_ids.resolve_player_name(p.name, p.color): General(p.general)
            for p in g.roster().humans
            if p.has_known_general
        }
    totals: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    for d in details:
        general_by_player = general_by_match.get(d.match_id)
        if not general_by_player:
            continue
        for ps in d.player_summary:
            resolved = player_ids.resolve_player_name(ps.name, ps.color)
            # general_by_player is built from roster().humans, so an AI's name
            # simply isn't in it - no separate CPU-name check needed.
            general = general_by_player.get(resolved)
            if general is None:
                continue
            totals[general][0] += ps.value_destroyed
            totals[general][1] += ps.value_lost
    return {g: (v[0], v[1]) for g, v in totals.items()}


def value_stats_from_computed(stats: list[Statistic]) -> dict[General, tuple[int, int]]:
    """Decode the `__general_value_*` rows persisted by the nightly recompute
    (see computed_stats.recompute) back into the same shape
    `general_value_stats` produces, for `get_generals_stats` to merge in."""
    destroyed: dict[General, int] = {}
    lost: dict[General, int] = {}
    for s in stats:
        if not s.stat_name.startswith(GENERAL_VALUE_STAT_PREFIX) or s.player is None:
            continue
        general = General(int(s.player))
        value = int(s.value or 0)
        if s.stat_name.endswith("destroyed"):
            destroyed[general] = value
        elif s.stat_name.endswith("lost"):
            lost[general] = value
    return {
        g: (destroyed.get(g, 0), lost.get(g, 0)) for g in destroyed.keys() | lost.keys()
    }


def get_generals_stats(
    games: list[MatchInfo], value_stats: dict[General, tuple[int, int]] | None = None
) -> GeneralStats:
    general_stats: dict[General, GeneralStat] = {}
    for game in games:
        if game.incomplete or game.winning_team < 1:
            continue
        if not game_composition.competitive_game_filter(game.composition):
            continue
        roster = game.roster()
        if len(roster.cpus) > 1:
            continue
        for player in roster.humans:
            general = General(player.general)
            if general not in general_stats:
                general_stats[general] = GeneralStat(
                    general=general,
                    stats=[],
                    total=WinLoss(wins=0, losses=0),
                )
            if not player.has_known_general:
                continue
            if player.won:
                general_stats[general].total.wins += 1
            else:
                general_stats[general].total.losses += 1

    filtered = [
        s
        for s in sorted(general_stats.values(), key=lambda x: x.general)
        if (s.total.wins + s.total.losses) > 0
    ]
    value_stats = value_stats or {}
    for s in filtered:
        s.value_destroyed, s.value_lost = value_stats.get(s.general, (0, 0))

    wins = sum(s.total.wins for s in general_stats.values())
    losses = sum(s.total.losses for s in general_stats.values())
    logger.info("totals", wins=wins, losses=losses)
    return GeneralStats(general_stats=filtered)


def get_general_matchups(games: list[MatchInfo]) -> GeneralMatchups:
    """Actual record for every pair of generals that has faced off, across
    whatever mix of formats `games` holds (the caller narrows by `gameFormat`
    the same way `get_generals_stats` does).

    For a 1v1 this is one winner-general-vs-loser-general sample per game. For
    a team game it's every general on the winning side crossed with every
    general on the losing side - a 2v2 contributes 4 samples, a 3v3 contributes
    9 - which is the standard way to turn a team result into pairwise matchup
    evidence (it's *within*-game correlated, unlike an independent draw, but
    it's the same tradeoff `general_value_stats` and every other per-general
    stat on this page already makes by crediting a team's win to each of its
    generals). Same-general pairs (a mirror matchup) carry no A-vs-B signal
    and are skipped. One row per unordered pair; the route/frontend fill in
    both directions of the grid from it.
    """
    pair_wins: dict[tuple[General, General], list[int]] = defaultdict(lambda: [0, 0])
    for game in games:
        if game.incomplete or game.winning_team < 1:
            continue
        if not game_composition.competitive_game_filter(game.composition):
            continue
        roster = game.roster()
        if len(roster.cpus) > 1:
            continue
        humans = roster.humans
        winners = [p for p in humans if p.won and p.has_known_general]
        losers = [p for p in humans if not p.won and p.has_known_general]
        for winner in winners:
            gen_w = General(winner.general)
            for loser in losers:
                gen_l = General(loser.general)
                if gen_w == gen_l:
                    continue
                key, winner_is_first = (
                    ((gen_w, gen_l), True) if gen_w < gen_l else ((gen_l, gen_w), False)
                )
                pair_wins[key][0 if winner_is_first else 1] += 1

    cells = [
        GeneralMatchupCell(general_a=a, general_b=b, a_wins=wl[0], b_wins=wl[1])
        for (a, b), wl in sorted(pair_wins.items(), key=lambda kv: kv[0])
    ]
    return GeneralMatchups(cells=cells)
