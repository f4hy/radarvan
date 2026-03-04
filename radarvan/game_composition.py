import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict
from typing import Protocol, Literal
from .db import MatchPlayer

logger = logging.getLogger(__name__)


class Player(Protocol):
    @property
    def Team(self) -> int:
        """Team the player is on."""

    @property
    def Type(self) -> Literal["H", "C"]:
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

    Args:
        players: list of Player objects

    Returns:
        GameComposition object with detailed game information
    """
    logger.info(f"Computing match comp on {players}")
    total_players = len(players)
    num_humans = sum(1 for p in players if p.Type == "H")
    num_computers = sum(1 for p in players if p.Type == "C")

    def create_composition(
        category: str,
        is_comp_stomp: bool,
        is_ffa: bool,
        num_teams: int,
        team_sizes: list[int],
    ) -> GameComposition:
        """Helper to create GameComposition with computed fields."""
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
        return create_composition("Unknown", False, False, 0, [])

    if len(players) == 1:
        return create_composition("Unknown", False, False, 1, [1])

    # Count players per team
    team_counts = Counter(player.Team for player in players)

    # Team 0 means no team (FFA players)
    ffa_player_count = team_counts.get(0, 0) + team_counts.get(-1, 0)
    valid_teams = {team: count for team, count in team_counts.items() if team > 0}

    num_teams = len(valid_teams)
    team_sizes = sorted(valid_teams.values()) if valid_teams else []

    if len(players) == 2:
        return create_composition("1v1", False, False, 2, [1, 1])

    # Case 1: Mixed FFA and team players
    if ffa_player_count > 0 and valid_teams:
        return create_composition("FFA", False, True, num_teams, team_sizes)

    # Case 2: All players on Team 0
    if ffa_player_count == len(players):
        category = "1v1" if len(players) == 2 else "FFA"
        return create_composition(category, False, category == "FFA", 0, [])

    # Case 3: No valid teams
    if not valid_teams:
        return create_composition("Unknown", False, False, 0, [])

    # Case 4: Everyone on different teams
    if num_teams == len(players):
        category = "1v1" if len(players) == 2 else "FFA"
        return create_composition(
            category, False, category == "FFA", num_teams, team_sizes
        )

    # Case 5: Everyone on the same team
    if num_teams == 1:
        return create_composition("FFA", False, True, num_teams, team_sizes)

    # Check for CompStomp
    team_compositions = {}
    for player in players:
        if player.Team > 0:
            if player.Team not in team_compositions:
                team_compositions[player.Team] = {"humans": 0, "computers": 0}
            if player.Type == "H":
                team_compositions[player.Team]["humans"] += 1
            elif player.Type == "C":
                team_compositions[player.Team]["computers"] += 1

    human_only_teams = [
        team
        for team, comp in team_compositions.items()
        if comp["humans"] > 0 and comp["computers"] == 0
    ]
    computer_only_teams = [
        team
        for team, comp in team_compositions.items()
        if comp["computers"] > 0 and comp["humans"] == 0
    ]

    is_comp_stomp = False
    if len(human_only_teams) >= 1 and len(computer_only_teams) >= 1:
        if len(human_only_teams) + len(computer_only_teams) == num_teams:
            is_comp_stomp = True

    # Determine category string
    if num_teams == 2:
        category = f"{team_sizes[0]}v{team_sizes[1]}"
    elif num_teams > 2:
        if len(set(team_sizes)) == 1:
            category = "v".join([str(team_sizes[0])] * num_teams)
        else:
            category = "FFA"
    else:
        category = "Unknown"

    return create_composition(
        category, is_comp_stomp, category == "FFA", num_teams, team_sizes
    )


# Matches the CPU name check in api_types.Player.Type
_CPU_NAMES = frozenset({"cpu", "hardai", "hardarmy", "mediai", "easyai"})


@dataclass
class _MatchPlayerAdapter:
    """Adapts a DB MatchPlayer to satisfy the Player protocol."""

    player: MatchPlayer

    @property
    def Team(self) -> int:
        return self.player.team_id

    @property
    def Type(self) -> Literal["H", "C"]:
        return "C" if self.player.player_name.lower() in _CPU_NAMES else "H"


def compute_match_composition(players: Sequence[MatchPlayer]) -> GameComposition:
    """Compute match composition from DB MatchPlayer records.

    Separated from persistence so it can be reused outside of the DB layer.
    """
    adapters = [_MatchPlayerAdapter(p) for p in players]
    return categorize_game_type(adapters)


def filter_by_format(
    games: list, game_format: str | None
) -> list:
    """Filter a list of MatchInfo by composition category. Returns unchanged list if format is None."""
    if game_format is None:
        return games
    return [
        g
        for g in games
        if g.composition is not None and g.composition.category == game_format
    ]


def competitive_game_filter(comp: GameComposition | None) -> bool:
    if comp is None:
        return False
    if comp.num_computers > 1:
        return False
    if comp.is_comp_stomp:
        return False
    if not comp.is_balanced:
        return False
    if not comp.is_team_game:
        return False
    return True
