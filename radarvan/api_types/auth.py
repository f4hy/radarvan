"""Session identity and account selection."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, computed_field
from ..player_ids import (
    is_admin as _is_admin_player,
    is_tournament_admin as _is_tournament_admin_player,
)
from .common import _FROM_ATTRIBUTES


class CurrentUser(BaseModel):
    model_config = _FROM_ATTRIBUTES

    discord_id: str
    discord_username: str
    discord_avatar: str | None = None
    player_name: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def needs_player_selection(self) -> bool:
        """True until the user has claimed an in-game name from PLAYER_NAMES."""
        return self.player_name is None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_admin(self) -> bool:
        """True if the claimed in-game name is in player_ids.ADMIN_PLAYERS."""
        return _is_admin_player(self.player_name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_tournament_admin(self) -> bool:
        """True if the claimed in-game name is in player_ids.TOURNAMENT_ADMINS."""
        return _is_tournament_admin_player(self.player_name)


class AuthStatus(BaseModel):
    logged_in: bool
    user: CurrentUser | None = None
    # The in-game names a logged-in user may claim (sorted PLAYER_NAMES).
    available_players: list[str] = Field(default_factory=list)


class SelectPlayerRequest(BaseModel):
    player_name: str
