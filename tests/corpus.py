"""A small, shared corpus of ``MatchInfo`` fixtures.

Several test modules each grew their own ``_match``/``_comp`` helper. This is the
one place to build match fixtures from, so a schema change to ``MatchInfo`` is a
single edit rather than eleven.

The corpus is deliberately fixed and deterministic: every id, timestamp, map and
roster is stable across runs, so tests can assert on derived values (ratings,
records, superlatives) without seeding randomness. Player names are real entries
in ``player_ids.PLAYER_NAMES`` - the competitive-match filter drops any team
without a known player, so made-up names would silently empty the corpus.
"""

from datetime import UTC, date, datetime

from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.game_composition import GameComposition
from radarvan.player_role import PlayerRole

# Known players, two per team, so every match passes
# ``player_ids.all_teams_have_group_player``.
TEAM_ONE = ("Skip", "CoreDawg")
TEAM_TWO = ("Syn", "Pancake")

# Six more known names, for FFAs that need more than the four team regulars.
FFA_NAMES = ("Skip", "CoreDawg", "Syn", "Pancake", "Neo", "Modus", "Tytan", "Shifty")

MAPS = ["Tournament Desert", "Bitter Winter", "Wasteland Warlords"]

COLORS = ("red", "blue", "green", "orange", "purple", "yellow", "pink", "cyan")

# All fixtures sit inside one month so relative-date filters (last 7/14/30 days)
# behave predictably relative to LATEST.
FIRST_DAY = date(2026, 1, 5)
LATEST = datetime(2026, 1, 28, 12, 0, tzinfo=UTC)


def composition(category: str = "2v2", **overrides: object) -> GameComposition:
    """A balanced, competitive composition; override fields to break that."""
    base: dict[str, object] = {
        "category": category,
        "is_comp_stomp": False,
        "is_ffa": False,
        "num_teams": 2,
        "team_sizes": [2, 2],
        "total_players": 4,
        "num_humans": 4,
        "num_computers": 0,
        "is_balanced": True,
        "is_1v1": category == "1v1",
        "is_team_game": True,
    }
    base.update(overrides)
    return GameComposition(**base)  # type: ignore[arg-type]


def match(
    match_id: int,
    *,
    day: int,
    winner: Team = Team.ONE,
    team_one: tuple[str, ...] = TEAM_ONE,
    team_two: tuple[str, ...] = TEAM_TWO,
    map_name: str | None = None,
    duration_minutes: float = 15.0,
    incomplete: str = "",
    comp: GameComposition | None = None,
    extra_players: tuple[Player, ...] = (),
) -> MatchInfo:
    """One match on 2026-01-``day``, team_one vs team_two.

    ``extra_players`` appends slots that are not part of either team - use
    ``observer()`` or ``cpu()`` to build them. They are deliberately *not*
    folded into the generated composition: an observer must not change any
    answer about the match (see CLAUDE.md), and the tests that assert that
    need a match whose composition is identical with and without them.
    """
    roster = [(n, Team.ONE) for n in team_one] + [(n, Team.TWO) for n in team_two]
    players = [
        Player(
            name=name,
            general=General(i % 12),
            team=team,
            color=COLORS[i % len(COLORS)],
            won=team == winner,
            starting_position=i,
        )
        for i, (name, team) in enumerate(roster)
    ]
    players += list(extra_players)
    if comp is None:
        size = len(team_one)
        comp = composition(
            category=f"{size}v{len(team_two)}",
            team_sizes=[size, len(team_two)],
            total_players=len(roster),
            num_humans=len(roster),
        )
    timestamp = datetime(2026, 1, day, 12, 0, tzinfo=UTC)
    return MatchInfo(
        id=match_id,
        timestamp=timestamp,
        date=timestamp.date(),
        map=map_name or MAPS[match_id % len(MAPS)],
        winning_team=winner,
        players=players,
        duration_minutes=duration_minutes,
        filename=f"match_{match_id}.rep",
        incomplete=incomplete,
        notes=incomplete,
        game_version="1.04",
        composition=comp,
        is_dev=False,
    )


def observer(
    name: str = "Gorn",
    color: str = "cyan",
    *,
    general: General = General.UNRECOGNIZED,
) -> Player:
    """A spectator slot: team OBSERVER, and by default no general.

    Adding one must never change an answer about the match. That has broken
    twice for real (see CLAUDE.md), so several modules here assert it directly.

    Pass a real ``general`` to make the assertion sharper. With the default, a
    consumer that filters on ``has_known_general`` drops the slot for the wrong
    reason and still looks correct; a spectator holding a recognized general can
    only be excluded by its *role*, which is the property actually under test.
    """
    return Player(
        name=name,
        general=general,
        team=Team.OBSERVER,
        color=color,
        won=False,
        role=PlayerRole.OBSERVER,
    )


def cpu(
    name: str = "TacticalAI",
    team: Team = Team.TWO,
    *,
    won: bool = False,
    color: str = "yellow",
    general: General = General.USA,
) -> Player:
    """An AI slot. ``role`` is set explicitly rather than left to the name
    fallback, because the header is what's authoritative in real data."""
    return Player(
        name=name,
        general=general,
        team=team,
        color=color,
        won=won,
        role=PlayerRole.CPU,
    )


def ffa_match(
    match_id: int,
    *,
    day: int,
    names: tuple[str, ...] = FFA_NAMES[:4],
    winner_index: int = 0,
    map_name: str | None = None,
    incomplete: str = "",
    num_computers: int = 0,
    generals: tuple[General, ...] | None = None,
) -> MatchInfo:
    """A free-for-all: every player teamless, exactly one winner.

    FFA slots are typically all team 0, which is why ``ffa_stats`` reads
    ``roster().humans`` rather than ``human_participants`` - requiring a team
    would empty the field. Built here so that shape is stated once.
    """
    players = [
        Player(
            name=name,
            general=(generals[i] if generals else General(i % 12)),
            team=Team.NONE,
            color=COLORS[i % len(COLORS)],
            won=(i == winner_index),
            starting_position=i,
        )
        for i, name in enumerate(names)
    ]
    n = len(names)
    comp = composition(
        category="ffa",
        is_ffa=True,
        is_team_game=False,
        is_1v1=False,
        num_teams=n,
        team_sizes=[1] * n,
        total_players=n + num_computers,
        num_humans=n,
        num_computers=num_computers,
    )
    timestamp = datetime(2026, 1, day, 12, 0, tzinfo=UTC)
    return MatchInfo(
        id=match_id,
        timestamp=timestamp,
        date=timestamp.date(),
        map=map_name or MAPS[match_id % len(MAPS)],
        winning_team=Team.NONE,
        players=players,
        duration_minutes=15.0,
        filename=f"ffa_{match_id}.rep",
        incomplete=incomplete,
        notes=incomplete,
        game_version="1.04",
        composition=comp,
        is_dev=False,
    )


def rated_corpus(games: int = 46) -> list[MatchInfo]:
    """Enough 2v2s that all four regulars clear ``player_rating.MIN_GAMES``.

    The default CORPUS is 15 games, so every rating derived from it is filtered
    out and any assertion about ratings passes for the wrong reason. Anything
    testing real rating output needs this instead.
    """
    return [
        match(8000 + i, day=5 + (i % 23), winner=Team.ONE if i % 3 else Team.TWO)
        for i in range(games)
    ]


def _build() -> list[MatchInfo]:
    """Twelve 2v2s, two 1v1s, and one incomplete game."""
    out = [
        match(9000 + i, day=5 + i, winner=Team.ONE if i % 3 else Team.TWO)
        for i in range(12)
    ]
    out += [
        match(
            9100 + i,
            day=20 + i,
            winner=Team.ONE if i else Team.TWO,
            team_one=(TEAM_ONE[0],),
            team_two=(TEAM_TWO[0],),
        )
        for i in range(2)
    ]
    out.append(match(9200, day=28, incomplete="Disconnect"))
    return out


CORPUS: list[MatchInfo] = _build()

# Handy references for tests that need a concrete id/name/date.
A_MATCH = CORPUS[0]
A_MAP = MAPS[0]
A_PLAYER = TEAM_ONE[0]
AN_OPPONENT = TEAM_TWO[0]
