"""Compute statistics scoped to free-for-all (FFA) games.

FFA games are every-player-for-themselves matches (``composition.is_ffa``). They
are excluded from the competitive leaderboards (which require balanced teams), so
they get their own page. The headline numbers are per-player win counts/games and
per-general win rates; we also surface FFA map activity.

Win rate alone is misleading in FFA because the expected rate is ``1/N`` for an
N-player game. We therefore also track *expected wins* (the sum of ``1/N`` over a
player's games) and a *dominance* ratio (actual wins / expected wins) so a player
who wins half of their 6-player FFAs reads as the outlier they are.
"""

from collections import Counter, defaultdict

from .api_types import (
    MatchInfo,
    General,
    FFAStats,
    FFAPlayerStat,
    FFAGeneralStat,
    FFAMapStat,
    FFARecentMatch,
)
from . import player_ids
import structlog

logger = structlog.get_logger(__name__)

CPU_NAMES = set(player_ids.CPU_NAME_MAPPING.values())

# Minimum FFA games before a player appears on the leaderboard.
MIN_PLAYER_GAMES = 8
# Minimum FFA games on a map before it shows up in the map breakdown.
MIN_MAP_GAMES = 2
# Smallest FFA we count (3+ humans, every-player-for-themselves).
MIN_FFA_PLAYERS = 3
# Cap the map list so the page stays readable.
TOP_MAPS = 15


def is_ffa_game(game: MatchInfo) -> bool:
    """True for a completed, human-only free-for-all we want to count.

    Comp-stomps and games containing any CPU are excluded so the stats reflect
    real players battling each other.
    """
    # NB: we deliberately do *not* call ``game_composition.competitive_game_filter``
    # here - it requires ``is_team_game`` and so would drop every FFA. The
    # ``num_computers > 0`` guard below covers the same "no CPUs" intent.
    comp = game.composition
    if game.incomplete:
        return False
    if comp is None or not comp.is_ffa:
        return False
    if comp.num_computers > 0:
        return False
    return not comp.num_humans < MIN_FFA_PLAYERS


def get_ffa_stats(games: list[MatchInfo]) -> FFAStats:
    player_games: Counter[str] = Counter()
    player_wins: Counter[str] = Counter()
    player_expected: defaultdict[str, float] = defaultdict(float)

    gen_games: Counter[General] = Counter()
    gen_wins: Counter[General] = Counter()

    map_games: Counter[str] = Counter()
    map_players: Counter[str] = Counter()

    total_games = 0
    total_slots = 0

    most_recent: FFARecentMatch | None = None
    most_recent_timestamp = None

    for game in games:
        if not is_ffa_game(game):
            continue

        # Resolve aliases and drop any stray CPU/observer slots before counting.
        entries = []
        for player in game.players:
            if not player.is_real():
                continue
            name = player_ids.resolve_player_name(player.name, player.color)
            if name in CPU_NAMES:
                continue
            entries.append((player, name))

        n = len(entries)
        if n < MIN_FFA_PLAYERS:
            continue

        total_games += 1
        total_slots += n
        map_games[game.map] += 1
        map_players[game.map] += n
        expected_per_player = 1.0 / n

        for player, name in entries:
            player_games[name] += 1
            player_expected[name] += expected_per_player
            gen_games[player.general] += 1

            if player.won:
                player_wins[name] += 1
                gen_wins[player.general] += 1

        if most_recent_timestamp is None or game.timestamp > most_recent_timestamp:
            winner_name = next((name for p, name in entries if p.won), None)
            if winner_name is not None:
                most_recent_timestamp = game.timestamp
                most_recent = FFARecentMatch(match_id=game.id, winner=winner_name)

    player_stats = [
        FFAPlayerStat(
            name=name,
            games=games_played,
            wins=player_wins[name],
            win_rate=player_wins[name] / games_played,
            expected_wins=player_expected[name],
            dominance=(
                player_wins[name] / player_expected[name]
                if player_expected[name] > 0
                else 0.0
            ),
        )
        for name, games_played in player_games.items()
        if games_played >= MIN_PLAYER_GAMES
    ]
    player_stats.sort(key=lambda s: (s.wins, s.dominance), reverse=True)

    general_stats = [
        FFAGeneralStat(
            general=general,
            games=games_played,
            wins=gen_wins[general],
            win_rate=gen_wins[general] / games_played,
        )
        for general, games_played in gen_games.items()
        if general != General.UNRECOGNIZED and games_played > 0
    ]
    general_stats.sort(key=lambda s: s.general)

    map_stats = [
        FFAMapStat(
            map=map_name,
            games=played,
            avg_players=map_players[map_name] / played,
        )
        for map_name, played in map_games.items()
        if played >= MIN_MAP_GAMES
    ]
    map_stats.sort(key=lambda s: s.games, reverse=True)
    map_stats = map_stats[:TOP_MAPS]

    avg_players = total_slots / total_games if total_games else 0.0
    logger.info(
        "computed ffa stats", total_games=total_games, players=len(player_games)
    )

    return FFAStats(
        total_games=total_games,
        distinct_players=len(player_games),
        avg_players_per_game=avg_players,
        most_recent=most_recent,
        player_stats=player_stats,
        general_stats=general_stats,
        map_stats=map_stats,
    )
