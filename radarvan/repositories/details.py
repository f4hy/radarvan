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

from sqlalchemy import delete as sa_delete, select

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

    def get_cached_kill_data_rows(
        self, match_ids: list[int], version: str
    ) -> dict[int, tuple[list[object], list[object]]]:
        """Return (killEvents, playerSummary) - as raw JSON, unvalidated - for
        whichever of `match_ids` have a cached row at `version`, in one query.

        Pulls those two JSONB paths server-side (`data['killEvents']` /
        `data['playerSummary']`) rather than selecting the whole `data`
        column: `data` is the *full* MatchDetails payload (build_orders,
        apm_over_time, timeline_events, stats_data, ...), and for a caller
        that only wants these two fields across many matches (e.g.
        head_to_head's value_destroyed_by_match, which can span hundreds of
        matches for a long-running matchup) transferring the whole blob per
        row is the dominant cost against a remote DB - degrees more than
        either per-match model validation or even one-round-trip-vs-many.
        Never falls back to S3 - a match missing from the result is simply
        omitted rather than paying for a full recompute.
        """
        if not match_ids:
            return {}
        stmt = select(
            MatchDetailsCache.match_id,
            MatchDetailsCache.data["killEvents"],
            MatchDetailsCache.data["playerSummary"],
        ).where(
            MatchDetailsCache.match_id.in_(match_ids),
            MatchDetailsCache.version == version,
        )
        rows = self.session.execute(stmt).all()
        return {
            match_id: (kill_events or [], player_summary or [])
            for match_id, kill_events, player_summary in rows
        }

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

        A debugging hatch: normal invalidation is per-match via
        delete_cached_details (reparse) or implicit via the DETAILS_VERSION
        check - derivation changes should bump the version, not call this.
        """
        result = self.session.execute(sa_delete(MatchDetailsCache))
        self._commit_if_auto()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]
