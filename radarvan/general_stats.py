"""Compute generals stats."""

from collections import defaultdict

from .api_types import (
    MatchInfo,
    General,
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


CPU_NAMES = set(player_ids.CPU_NAME_MAPPING.values())

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
    not live per-request - see routes/superlatives._do_recompute.
    """
    general_by_match: dict[int, dict[str, General]] = {}
    for g in games:
        general_by_match[g.id] = {
            player_ids.resolve_player_name(p.name, p.color): p.general
            for p in g.players
            if p.is_real()
        }
    totals: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    for d in details:
        general_by_player = general_by_match.get(d.match_id)
        if not general_by_player:
            continue
        for ps in d.player_summary:
            resolved = player_ids.resolve_player_name(ps.name, ps.color)
            if resolved in CPU_NAMES:
                continue
            general = general_by_player.get(resolved)
            if general is None:
                continue
            totals[general][0] += ps.value_destroyed
            totals[general][1] += ps.value_lost
    return {g: (v[0], v[1]) for g, v in totals.items()}


def value_stats_from_computed(stats: list[Statistic]) -> dict[General, tuple[int, int]]:
    """Decode the `__general_value_*` rows persisted by the nightly recompute
    (see routes/superlatives._do_recompute) back into the same shape
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
        resolved = [
            player_ids.resolve_player_name(p.name, p.color) for p in game.players
        ]
        if sum(1 for n in resolved if n in CPU_NAMES) > 1:
            continue
        for player, name in zip(game.players, resolved, strict=True):
            if player.general not in general_stats:
                general_stats[player.general] = GeneralStat(
                    general=player.general,
                    stats=[],
                    total=WinLoss(wins=0, losses=0),
                )
            if not player.is_real():
                continue
            if name in CPU_NAMES:
                continue
            if player.won:
                general_stats[player.general].total.wins += 1
            else:
                general_stats[player.general].total.losses += 1

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
