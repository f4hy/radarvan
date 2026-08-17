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

# Known players, two per team, so every match passes
# ``player_ids.all_teams_have_group_player``.
TEAM_ONE = ("Skip", "CoreDawg")
TEAM_TWO = ("Syn", "Pancake")

MAPS = ["Tournament Desert", "Bitter Winter", "Wasteland Warlords"]

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
) -> MatchInfo:
    """One match on 2026-01-``day``, team_one vs team_two."""
    roster = [(n, Team.ONE) for n in team_one] + [(n, Team.TWO) for n in team_two]
    colors = ["red", "blue", "green", "orange", "purple", "yellow", "pink", "cyan"]
    players = [
        Player(
            name=name,
            general=General(i % 12),
            team=team,
            color=colors[i % len(colors)],
            won=team == winner,
            starting_position=i,
        )
        for i, (name, team) in enumerate(roster)
    ]
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
