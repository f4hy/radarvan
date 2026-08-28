"""Compute statistics scoped to free-for-all (FFA) games.

FFA games are every-player-for-themselves matches (``composition.is_ffa``). They
are excluded from the competitive leaderboards (which require balanced teams), so
they get their own page. The headline numbers are per-player win counts/games and
per-general win rates; we also surface FFA map activity.

``include_cpu`` selects the corpus, and the page offers it as a toggle. Off (the
default) is the human-only field this module started as. On, AI slots are *full
participants* rather than merely tolerated: they count toward the field size, so
beating three Tactical AIs reads as the 4-player field it was; they get their own
leaderboard rows and their generals join the win-rate table; and an FFA the AI
won is a win for that AI rather than a game with no winner. That is one switch -
which roster partition ``entries`` is built from - because a half-counted CPU
(present in the field, absent from the totals) is exactly the kind of asymmetry
that makes two numbers on the same page disagree.

One consequence of that, visible on the leaderboard: a game can field three
slots all called "Tactical AI", and they collapse into a single row whose
``games`` therefore counts *slots*, not matches (145 of them across 151 games in
the current corpus). ``expected_wins`` collapses the same way - three slots at
1/N each - so ``dominance``, the number that judgment hangs on, stays honest.

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

# Minimum FFA games before a player appears on the leaderboard.
MIN_PLAYER_GAMES = 8
# Minimum FFA games on a map before it shows up in the map breakdown.
MIN_MAP_GAMES = 2
# Smallest FFA we count: 3+ in the field, every player for themselves.
# Whether AI slots count toward that field is `include_cpu`'s decision.
MIN_FFA_PLAYERS = 3
# Cap the map list so the page stays readable.
TOP_MAPS = 15


def is_ffa_game(game: MatchInfo, *, include_cpu: bool = False) -> bool:
    """True for a completed free-for-all we want to count.

    With ``include_cpu`` false (the default) any game containing a CPU is
    dropped, so the stats reflect real players battling each other. With it
    true, AI slots count toward the field, so the size floor is measured
    against the whole field rather than the humans in it - a 2-human, 4-CPU
    game is a 6-player free-for-all.
    """
    # NB: we deliberately do *not* call ``game_composition.competitive_game_filter``
    # here - it requires ``is_team_game`` and so would drop every FFA. The
    # ``num_computers`` guard below covers the same "no CPUs" intent.
    comp = game.composition
    if game.incomplete:
        return False
    if comp is None or not comp.is_ffa:
        return False
    if not include_cpu:
        return comp.num_computers == 0 and comp.num_humans >= MIN_FFA_PLAYERS
    return comp.num_humans + comp.num_computers >= MIN_FFA_PLAYERS


def get_ffa_stats(games: list[MatchInfo], *, include_cpu: bool = False) -> FFAStats:
    player_games: Counter[str] = Counter()
    player_wins: Counter[str] = Counter()
    player_expected: defaultdict[str, float] = defaultdict(float)
    # Which leaderboard rows are AI, so the page can mark them rather than
    # offering a player profile for "Tactical AI". Stays empty when
    # `include_cpu` is off.
    cpu_names: set[str] = set()

    gen_games: Counter[General] = Counter()
    gen_wins: Counter[General] = Counter()

    map_games: Counter[str] = Counter()
    map_players: Counter[str] = Counter()

    total_games = 0
    total_slots = 0

    most_recent: FFARecentMatch | None = None
    most_recent_timestamp = None

    for game in games:
        if not is_ffa_game(game, include_cpu=include_cpu):
            continue

        roster = game.roster()
        # roster().humans drops observers and AI in one go. Deliberately not
        # `human_participants`: an FFA's slots are often all teamless (team 0),
        # so requiring a team here would empty the field.
        entries = [
            (p, player_ids.resolve_player_name(p.name, p.color))
            for p in roster.humans
            if p.has_known_general
        ]
        if include_cpu:
            # An AI's name arrives already canonical ("Tactical AI", "Hard
            # Army"); alias resolution exists for humans' in-game spellings and
            # here could only risk folding a CPU onto a person.
            ai = [(p, p.name) for p in roster.cpus if p.has_known_general]
            cpu_names.update(name for _, name in ai)
            entries += ai

        n = len(entries)
        if n < MIN_FFA_PLAYERS:
            continue

        total_games += 1
        total_slots += n
        map_games[game.map] += 1
        map_players[game.map] += n
        expected_per_player = 1.0 / n

        for player, name in entries:
            general = General(player.general)
            player_games[name] += 1
            player_expected[name] += expected_per_player
            gen_games[general] += 1

            if player.won:
                player_wins[name] += 1
                gen_wins[general] += 1

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
            is_cpu=name in cpu_names,
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
        # No UNRECOGNIZED check: `entries` above already drops any slot failing
        # has_known_general (general < 0), so one can never reach gen_games.
        if games_played > 0
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
        "computed ffa stats",
        total_games=total_games,
        players=len(player_games),
        include_cpu=include_cpu,
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
