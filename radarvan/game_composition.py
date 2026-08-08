"""Game-type categorization (``categorize_game_type``) and the competitive-game filter
(``competitive_game_filter``) used to scope leaderboard stats to balanced, non-comp-stomp
team games."""

from __future__ import annotations

import structlog
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import NamedTuple
from pydantic import BaseModel, Field, ConfigDict
from typing import Protocol
from .db import MatchPlayer
from .player_role import PlayerRole, resolve_role

logger = structlog.get_logger(__name__)


class Player(Protocol):
    @property
    def team(self) -> int:
        """Team the player is on."""

    @property
    def type(self) -> str | None:
        """If its a human or cpu player."""


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class GameComposition(BaseModel):
    """
    Detailed composition information about an RTS game.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase
        slots=True,  # type: ignore[typeddict-unknown-key]
        json_schema_extra={
            "example": {
                "category": "2v2",
                "isCompStomp": False,
                "isFfa": False,
                "numTeams": 2,
                "teamSizes": [2, 2],
                "totalPlayers": 4,
                "numHumans": 3,
                "numComputers": 1,
                "isBalanced": True,
                "is1v1": False,
                "isTeamGame": True,
            }
        },
    )

    category: str = Field(
        ...,
        description="Game type category",
        examples=["1v1", "2v2", "3v4", "2v2v2", "FFA", "Unknown"],
    )
    is_comp_stomp: bool = Field(
        ..., description="True if all humans are on team(s) vs all computers"
    )
    is_ffa: bool = Field(..., description="True if this is a free-for-all game")
    num_teams: int = Field(..., ge=0, description="Number of teams in the game")
    team_sizes: list[int] = Field(
        ..., description="Sorted list of team sizes, empty for FFA with Team=0"
    )
    total_players: int = Field(
        ..., ge=0, description="Total number of players in the game"
    )
    num_humans: int = Field(..., ge=0, description="Number of human players")
    num_computers: int = Field(..., ge=0, description="Number of computer/AI players")

    # Computed fields
    is_balanced: bool = Field(
        default=False, description="True if all teams have the same number of players"
    )
    is_1v1: bool = Field(default=False, description="True if this is a 1v1 game")
    is_team_game: bool = Field(
        default=False, description="True if this is a team-based game (not FFA)"
    )


@dataclass(frozen=True, slots=True)
class RosterSlot:
    """One player slot, normalized away from whichever shape it arrived in.

    ``general`` is a raw ``api_types.General`` value rather than the enum -
    api_types imports this module, so the dependency can't run the other way.
    Negative means UNRECOGNIZED.
    """

    name: str
    color: str
    team: int
    general: int
    role: PlayerRole
    won: bool = False

    @property
    def has_known_general(self) -> bool:
        """False for observers and slots whose side the parser didn't recognize."""
        return self.general >= 0


class MatchRoster:
    """Who was in a match, partitioned once at construction.

    Built from whichever player shape the caller has (replay header, DB rows,
    or ``api_types.Player``), this is the one place that decides who is a
    spectator, who is an AI, and who is actually on a team. Consumers ask the
    roster instead of re-deriving it - the codebase previously carried three
    mutually inconsistent spellings of "skip the observers" (``team > 0``,
    ``team == Team.OBSERVER``, ``is_real()``) and two disagreeing CPU-name
    lists.

    Two distinctions that look alike but are not:

    - ``role`` separates spectators from people who played. It comes from the
      replay header and is authoritative.
    - ``team > 0`` separates slots placed on a real team from teamless ones. A
      1v1 that never went through ``reassign_1v1_teams`` has two teamless
      *competitors*, which is why ``participants`` and ``competitors`` are
      different properties and why the caller has to pick the right one.
    """

    __slots__ = ("_competitors", "_observers", "_participants", "_slots")

    def __init__(self, slots: Iterable[RosterSlot]) -> None:
        self._slots = tuple(slots)
        self._observers = tuple(
            s for s in self._slots if s.role is PlayerRole.OBSERVER
        )
        self._competitors = tuple(
            s for s in self._slots if s.role is not PlayerRole.OBSERVER
        )
        self._participants = tuple(s for s in self._competitors if s.team > 0)

    @classmethod
    def from_db_players(cls, players: Iterable[MatchPlayer]) -> MatchRoster:
        """Build from ``match_players`` rows, guessing role where unset."""
        return cls(
            RosterSlot(
                name=p.player_name,
                color=p.color,
                team=p.team_id,
                general=p.general_id,
                role=resolve_role(
                    p.role, p.player_name, p.color, is_observer=p.team_id < 0
                ),
                won=p.is_winner,
            )
            for p in players
        )

    @classmethod
    def from_players(cls, players: Iterable[RosterInput]) -> MatchRoster:
        """Build from anything with the ``api_types.Player`` shape."""
        return cls(
            RosterSlot(
                name=p.name,
                color=p.color,
                team=int(p.team),
                general=int(p.general),
                role=resolve_role(p.role, p.name, p.color, is_observer=p.team < 0),
                won=p.won,
            )
            for p in players
        )

    @property
    def slots(self) -> tuple[RosterSlot, ...]:
        """Every slot in the match, observers included."""
        return self._slots

    @property
    def observers(self) -> tuple[RosterSlot, ...]:
        """Spectators and empty/disconnected slots. Never played."""
        return self._observers

    @property
    def competitors(self) -> tuple[RosterSlot, ...]:
        """Everyone who played - humans and AI, teamless slots included."""
        return self._competitors

    @property
    def participants(self) -> tuple[RosterSlot, ...]:
        """Competitors placed on a real team (``team > 0``)."""
        return self._participants

    @property
    def humans(self) -> tuple[RosterSlot, ...]:
        return tuple(s for s in self._competitors if s.role is PlayerRole.HUMAN)

    @property
    def cpus(self) -> tuple[RosterSlot, ...]:
        return tuple(s for s in self._competitors if s.role is PlayerRole.CPU)

    @property
    def teams(self) -> dict[int, tuple[RosterSlot, ...]]:
        """Participants grouped by team id, in ascending team order."""
        grouped: dict[int, list[RosterSlot]] = {}
        for s in self._participants:
            grouped.setdefault(s.team, []).append(s)
        return {team: tuple(grouped[team]) for team in sorted(grouped)}

    def composition(self) -> GameComposition:
        """Categorize this match's game type."""
        return _composition_from_roster(self)


class RosterInput(Protocol):
    """The ``api_types.Player`` shape, structurally.

    Declared here rather than importing api_types, which imports this module.
    """

    @property
    def name(self) -> str: ...
    @property
    def color(self) -> str: ...
    @property
    def team(self) -> int: ...
    @property
    def general(self) -> int: ...
    @property
    def role(self) -> PlayerRole | None: ...
    @property
    def won(self) -> bool: ...


def categorize_game_type(players: Sequence[Player]) -> GameComposition:
    """Analyze the composition of an RTS game based on the player list.

    Back-compat entry point for callers holding the older ``(team, type)``
    shape; prefer building a ``MatchRoster`` and calling ``.composition()``.
    Callers of this form have already dropped observers upstream (via
    ``utils.is_competitor``), so every slot here is treated as a competitor.
    """
    return MatchRoster(
        RosterSlot(
            name="",
            color="",
            team=p.team,
            general=-1,
            role=PlayerRole.CPU if p.type == "C" else PlayerRole.HUMAN,
        )
        for p in players
    ).composition()


def _composition_from_roster(roster: MatchRoster) -> GameComposition:
    """
    Determine game type from a roster.

    Only ``participants`` (competitors on a real team) influence the
    determined game type; observers and teamless slots still count toward
    total_players. num_humans/num_computers count competitors by role, so
    spectators are in neither.
    """
    logger.debug("computing match comp", slots=roster.slots)
    players = roster.competitors
    total_players = len(roster.slots)
    num_humans = len(roster.humans)
    num_computers = len(roster.cpus)

    def create_composition(
        category: str,
        is_comp_stomp: bool,
        is_ffa: bool,
        team_sizes: list[int],
    ) -> GameComposition:
        """Helper to create GameComposition with computed fields."""
        num_teams = len(team_sizes)
        is_balanced = len(set(team_sizes)) <= 1 if team_sizes else False
        is_1v1 = category == "1v1"
        is_team_game = not is_ffa and num_teams >= 2

        return GameComposition(
            category=category,
            is_comp_stomp=is_comp_stomp,
            is_ffa=is_ffa,
            num_teams=num_teams,
            team_sizes=team_sizes,
            total_players=total_players,
            num_humans=num_humans,
            num_computers=num_computers,
            is_balanced=is_balanced,
            is_1v1=is_1v1,
            is_team_game=is_team_game,
        )

    if not players:
        return create_composition("Unknown", False, False, [])

    # Observers and teamless slots count toward total_players but must never
    # influence the determined game type, so every branch below reads
    # `participants`, not `players` - a 1v1 watched by two spectators is a
    # 1v1, not a four-player FFA.
    participants = roster.participants

    if not participants:
        # Nobody was given a real team, so there is no spectator/competitor
        # distinction to draw and every slot counts. Exactly two is a 1v1 that
        # never went through parse_replay.reassign_1v1_teams (old rows, and
        # replays where the lobby left both slots teamless); any more is a
        # genuine teamless free-for-all.
        if len(players) == 1:
            return create_composition("Unknown", False, False, [1])
        if len(players) == 2:
            return create_composition("1v1", False, False, [1, 1])
        return create_composition("FFA", False, True, [])

    if len(participants) == 1:
        return create_composition("Unknown", False, False, [1])

    if len(participants) == 2:
        return create_composition("1v1", False, False, [1, 1])

    team_counts = Counter(p.team for p in participants)
    num_teams = len(team_counts)
    team_sizes = sorted(team_counts.values())

    # Everyone in a team of their own is a free-for-all.
    if max(team_sizes) < 2:
        return create_composition("FFA", False, True, [])

    # Everyone on the same team
    if num_teams == 1:
        return create_composition("FFA", False, True, team_sizes)

    # Comp-stomp: every team is exclusively human or exclusively computer,
    # with at least one of each.
    human_teams = {p.team for p in participants if p.role is PlayerRole.HUMAN}
    computer_teams = {p.team for p in participants if p.role is PlayerRole.CPU}
    human_only_teams = human_teams - computer_teams
    computer_only_teams = computer_teams - human_teams
    is_comp_stomp = (
        bool(human_only_teams)
        and bool(computer_only_teams)
        and len(human_only_teams) + len(computer_only_teams) == num_teams
    )

    # Determine category string. num_teams >= 2 here - one team returned above.
    if num_teams == 2:
        category = f"{team_sizes[0]}v{team_sizes[1]}"
    elif len(set(team_sizes)) == 1:
        category = "v".join([str(team_sizes[0])] * num_teams)
    else:
        category = "FFA"

    return create_composition(category, is_comp_stomp, category == "FFA", team_sizes)


class PlayerAdapter(NamedTuple):
    """Adapt any player-like data to the Player protocol."""

    team: int
    type: str | None


def compute_match_composition(players: Sequence[MatchPlayer]) -> GameComposition:
    """Compute match composition from DB MatchPlayer records.

    Separated from persistence so it can be reused outside of the DB layer.
    """
    return MatchRoster.from_db_players(players).composition()


def is_recognized_team_game(comp: GameComposition | None) -> bool:
    """True for any parsed team-format game (not FFA), regardless of balance,
    CPU count, or comp-stomp status.

    Looser than ``competitive_game_filter`` on purpose: some callers (e.g. a
    "games played" tally) want to count comp-stomps and lopsided team games
    as real games without counting them as *competitive* results.
    """
    return comp is not None and comp.is_team_game


def competitive_game_filter(comp: GameComposition | None) -> bool:
    if comp is None:
        return False
    if comp.num_computers > 1:
        return False
    if comp.is_comp_stomp:
        return False
    if not comp.is_balanced:
        return False
    return comp.is_team_game
