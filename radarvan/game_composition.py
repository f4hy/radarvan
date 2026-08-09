"""Who was in a match, and what kind of match it was.

``MatchRoster`` is the single place the backend decides who spectated, who
played, and who was AI - build one from whichever shape you have (replay
header, ``match_players`` rows, or ``api_types.Player`` via
``MatchInfo.roster()``) and read its partitions instead of testing ``team`` or
matching names. ``GameComposition`` / ``competitive_game_filter`` are derived
from it and scope leaderboard stats to balanced, non-comp-stomp team games.
"""

from __future__ import annotations

import structlog
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict
from typing import Protocol
from .db import MatchPlayer
from .player_ids import PLAYER_NAMES, resolve_player_name
from .cncstats_model.header import Player as HeaderPlayer
from .player_role import (
    PlayerRole,
    normalize_color,
    resolve_role,
    role_from_header,
    start_position_from_header,
    team_from_header,
)

logger = structlog.get_logger(__name__)


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
    # 1-based, matching map-data player_number (see utils.players_from_replay).
    starting_position: int | None = None

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

    __slots__ = (
        "_competitors",
        "_cpus",
        "_human_participants",
        "_humans",
        "_participants",
        "_slots",
    )

    def __init__(self, slots: Iterable[RosterSlot]) -> None:
        # One pass, not one per partition: every stats module builds a roster
        # per match across thousands of matches. `observers` is derived on
        # demand instead - it's the complement of `competitors` and no hot
        # path reads it.
        self._slots = tuple(slots)
        competitors: list[RosterSlot] = []
        humans: list[RosterSlot] = []
        cpus: list[RosterSlot] = []
        participants: list[RosterSlot] = []
        human_participants: list[RosterSlot] = []
        for s in self._slots:
            if s.role is PlayerRole.OBSERVER:
                continue
            competitors.append(s)
            is_human = s.role is PlayerRole.HUMAN
            (humans if is_human else cpus).append(s)
            if s.team > 0:
                participants.append(s)
                if is_human:
                    human_participants.append(s)
        self._competitors = tuple(competitors)
        self._humans = tuple(humans)
        self._cpus = tuple(cpus)
        self._participants = tuple(participants)
        self._human_participants = tuple(human_participants)

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
                starting_position=p.starting_position,
            )
            for p in players
        )

    @classmethod
    def from_header_players(cls, players: Iterable[HeaderPlayer]) -> MatchRoster:
        """Build straight from a parsed replay header.

        The parse-time entry point, before anything has been written to the DB.
        Pass every header slot - the roster sorts spectators out itself, and
        filtering beforehand would undercount total_players relative to the
        DB-side roster.
        """
        return cls(
            RosterSlot(
                name=p.name,
                color=normalize_color(p.color),
                team=team_from_header(p),
                # The header carries no side; general is a summary field.
                general=-1,
                role=role_from_header(p),
                starting_position=start_position_from_header(p),
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
                starting_position=p.starting_position,
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
        return tuple(s for s in self._slots if s.role is PlayerRole.OBSERVER)

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
        """Human competitors, teamless slots included."""
        return self._humans

    @property
    def cpus(self) -> tuple[RosterSlot, ...]:
        """AI competitors, teamless slots included."""
        return self._cpus

    @property
    def human_participants(self) -> tuple[RosterSlot, ...]:
        """Humans on a real team - what per-player stats should count.

        Note this says nothing about whether the player's *general* parsed;
        callers that bucket by general must also check
        ``RosterSlot.has_known_general``, which is a parse-quality question
        rather than a role one.
        """
        return self._human_participants

    @property
    def has_cpu(self) -> bool:
        return bool(self._cpus)

    def all_teams_have_group_player(self) -> bool:
        """True if every team has at least one player from PLAYER_NAMES.

        A method on the roster rather than a free function taking players:
        it must only ever see competitors already on a team, and taking the
        partition from `self` is the only way to enforce that. Passing a raw
        player list buckets observers into team 0 and quietly returns False.
        """
        teams: dict[int, bool] = {}
        for s in self._participants:
            name = resolve_player_name(s.name, s.color)
            teams.setdefault(s.team, False)
            if name in PLAYER_NAMES:
                teams[s.team] = True
        return bool(teams) and all(teams.values())

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
    def starting_position(self) -> int | None: ...
    @property
    def team(self) -> int: ...
    @property
    def general(self) -> int: ...
    @property
    def role(self) -> PlayerRole | None: ...
    @property
    def won(self) -> bool: ...


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
