"""Session identity and account selection."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field
from ..player_ids import (
    is_admin as _is_admin_player,
    is_ops_admin as _is_ops_admin_player,
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
        """Whether this Discord account may use general admin features."""
        return _is_admin_player(self.discord_id)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_tournament_admin(self) -> bool:
        """Whether this Discord account may administer the tournament bracket."""
        return _is_tournament_admin_player(self.discord_id)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_ops_admin(self) -> bool:
        """Whether this Discord account may run operational admin tasks."""
        return _is_ops_admin_player(self.discord_id)


class AuthStatus(BaseModel):
    logged_in: bool
    user: CurrentUser | None = None
    # The in-game names a logged-in user may claim (sorted PLAYER_NAMES).
    available_players: list[str] = Field(default_factory=list)


class SelectPlayerRequest(BaseModel):
    player_name: str


class AdminUser(BaseModel):
    """Account details visible only to operations administrators."""

    model_config = _FROM_ATTRIBUTES

    id: int
    discord_id: str
    discord_username: str
    player_name: str | None = None
    created_at: datetime
