"""Game-type categorization (``categorize_game_type``) and the competitive-game filter
(``competitive_game_filter``) used to scope leaderboard stats to balanced, non-comp-stomp
team games."""

import structlog
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple
from pydantic import BaseModel, Field, ConfigDict
from typing import Protocol
from .db import MatchPlayer

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


def categorize_game_type(players: Sequence[Player]) -> GameComposition:
    """
    Analyze the composition of an RTS game based on the player list.

    Players on team <= 0 (spectators, disconnected slots) are filtered out
    before the game type is determined; they still count toward
    total_players/num_humans/num_computers.

    Args:
        players: list of Player objects

    Returns:
        GameComposition object with detailed game information
    """
    logger.debug("computing match comp", players=players)
    total_players = len(players)
    num_humans = sum(1 for p in players if p.type == "H")
    num_computers = sum(1 for p in players if p.type == "C")

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

    # Team <= 0 means "no team": spectators and disconnected slots. They count
    # toward total_players/num_humans but must never influence the determined
    # game type, so every branch below reads `participants`, not `players` - a
    # 1v1 watched by two spectators is a 1v1, not a four-player FFA.
    participants = [p for p in players if p.team > 0]

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
    human_teams = {p.team for p in participants if p.type == "H"}
    computer_teams = {p.team for p in participants if p.type == "C"}
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


# Matches the CPU name check in api_types.Player.Type
_CPU_NAMES = frozenset({"cpu", "hardai", "hardarmy", "mediai", "easyai"})


@dataclass(slots=True)
class _MatchPlayerAdapter:
    """Adapts a DB MatchPlayer to satisfy the Player protocol."""

    player: MatchPlayer

    @property
    def team(self) -> int:
        return self.player.team_id

    @property
    def type(self) -> str:
        return "C" if self.player.player_name.lower() in _CPU_NAMES else "H"


def compute_match_composition(players: Sequence[MatchPlayer]) -> GameComposition:
    """Compute match composition from DB MatchPlayer records.

    Separated from persistence so it can be reused outside of the DB layer.
    """
    adapters = [_MatchPlayerAdapter(p) for p in players]
    return categorize_game_type(adapters)


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
