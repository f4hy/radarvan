"""PlayerProfileCache repository.

A durable, versioned store of the per-player profile deep stats
(PlayerProfileComputed). Rows are stamped with the PROFILE_VERSION that
produced them; a read only returns a row whose version matches the caller's
current version. Profiles are always saved as a whole batch - percentiles are
relative to the profiled population, so per-player writes would skew them.
"""

from datetime import UTC, datetime

import structlog

from sqlalchemy import delete as sa_delete, func, select

from ..api_types import PlayerProfileComputed
from ..db import PlayerProfileCache

from .base import BaseRepo

logger = structlog.get_logger(__name__)


class ProfileRepo(BaseRepo):
    """Operations on PlayerProfileCache."""

    def get_player_profile(
        self, player: str, version: str
    ) -> PlayerProfileComputed | None:
        """Return the persisted deep stats iff a row exists at this version.

        A version mismatch (stale derivation) is treated as a miss; the row
        stays until the next batch recompute overwrites it.
        """
        row = self.session.get(PlayerProfileCache, player)
        if row is None or row.version != version:
            return None
        return PlayerProfileComputed.model_validate(row.data)

    def save_player_profiles(
        self, profiles: dict[str, PlayerProfileComputed], version: str
    ) -> None:
        """Replace all persisted profiles with this batch at the given version.

        Rows for players no longer in the batch are deleted so a player who
        drops below the games threshold doesn't keep serving stale stats.
        """
        self.session.execute(
            sa_delete(PlayerProfileCache).where(
                PlayerProfileCache.player.notin_(profiles.keys())
            )
        )
        for player, computed in profiles.items():
            # computed_at is set explicitly: session.merge() copies attribute
            # state by PK, and an unset onupdate column would merge as NULL
            # (rejected by NOT NULL on the update path). See CLAUDE.md gotcha.
            self.session.merge(
                PlayerProfileCache(
                    player=player,
                    version=version,
                    data=computed.model_dump(mode="json", by_alias=True),
                    computed_at=datetime.now(UTC),
                )
            )
        self._commit_if_auto()

    def list_profiled_players(self, version: str) -> list[str]:
        """Names of players with a persisted profile at this version.

        This is exactly the "active player" population the batch recompute
        used as peer baselines - and the version check means it reflects the
        most recent recompute, not a stale one from before the last logic
        change. Used to populate the profile page's player picker so it only
        offers players deep stats actually exist for.
        """
        stmt = (
            select(PlayerProfileCache.player)
            .where(PlayerProfileCache.version == version)
            .order_by(PlayerProfileCache.player)
        )
        return list(self.session.scalars(stmt).all())

    def player_profiles_are_stale(self, days: int = 3) -> bool:
        """True if no profiles exist or the newest is older than `days` days."""
        latest = self.session.scalar(select(func.max(PlayerProfileCache.computed_at)))
        if latest is None:
            return True
        return (datetime.now(UTC) - latest).days > days

    def delete_all_player_profiles(self) -> int:
        """Drop every row. Returns the number of rows deleted (debug hatch)."""
        result = self.session.execute(sa_delete(PlayerProfileCache))
        self._commit_if_auto()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]
