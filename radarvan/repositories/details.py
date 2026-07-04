"""MatchDetailsCache repository.

A durable, versioned cache of the derived MatchDetails wire shape. The raw
cncstats JSON stays in S3; this stores only the small, owned projection so the
request path doesn't re-read + re-validate the multi-MB blob on every hit, and
the cache survives process restarts. Rows are stamped with the DETAILS_VERSION
that produced them; a read only returns a row whose version matches the
caller's current version, so bumping the derivation invalidates every row.
"""

from datetime import UTC, datetime

import structlog

from sqlalchemy import delete as sa_delete

from ..api_types import MatchDetails
from ..db import MatchDetailsCache

from .base import BaseRepo

logger = structlog.get_logger(__name__)


class MatchDetailsRepo(BaseRepo):
    """Operations on MatchDetailsCache."""

    def get_cached_details(self, match_id: int, version: str) -> MatchDetails | None:
        """Return cached MatchDetails iff a row exists and its version matches.

        A version mismatch (stale derivation) is treated as a miss so the caller
        recomputes and overwrites the row.
        """
        row = self.session.get(MatchDetailsCache, match_id)
        if row is None or row.version != version:
            return None
        return MatchDetails.model_validate(row.data)

    def save_cached_details(
        self, match_id: int, details: MatchDetails, version: str
    ) -> None:
        """Upsert the derived MatchDetails for a match at the given version."""
        payload = details.model_dump(mode="json", by_alias=True)
        # computed_at is set explicitly: session.merge() copies attribute state
        # by PK, and an unset onupdate column would be merged as NULL (which a
        # NOT NULL column rejects on the update path). See CLAUDE.md gotcha.
        self.session.merge(
            MatchDetailsCache(
                match_id=match_id,
                version=version,
                data=payload,
                computed_at=datetime.now(UTC),
            )
        )
        self._commit_if_auto()

    def delete_cached_details(self, match_id: int) -> bool:
        """Drop the cached row for a match. Returns True if a row was deleted.

        Call after a reparse: the raw replay changed but DETAILS_VERSION did
        not, so the version check alone wouldn't invalidate the stale row.
        """
        result = self.session.execute(
            sa_delete(MatchDetailsCache).where(MatchDetailsCache.match_id == match_id)
        )
        self._commit_if_auto()
        return bool(result.rowcount)  # type: ignore[attr-defined]

    def delete_all_cached_details(self) -> int:
        """Drop every row. Returns the number of rows deleted.

        For a full manual cache bust (e.g. after a derivation change that a
        version bump should have caught but didn't, or while debugging) -
        normal invalidation is per-match via delete_cached_details, or
        implicit via the DETAILS_VERSION check.
        """
        result = self.session.execute(sa_delete(MatchDetailsCache))
        self._commit_if_auto()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]
