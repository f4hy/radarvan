"""Operations on MatchNetstatsRow."""

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import NamedTuple

import structlog
from pydantic import ValidationError
from sqlalchemy import delete, func

from ..api_types import NetstatsSummary
from ..db import Match, MatchNetstatsRow, NetstatsStatus
from .base import BaseRepo

logger = structlog.get_logger(__name__)


class NetstatsWork(NamedTuple):
    match_id: int
    attempts: int


class NetstatsRepo(BaseRepo):
    def get_summaries(self, match_ids: Iterable[int]) -> dict[int, NetstatsSummary]:
        """Stored summaries for ``match_ids``; a row that no longer validates is skipped."""
        ids = list(match_ids)
        if not ids:
            return {}
        rows = (
            self.session.query(MatchNetstatsRow.match_id, MatchNetstatsRow.summary)
            .filter(
                MatchNetstatsRow.match_id.in_(ids),
                MatchNetstatsRow.status == NetstatsStatus.OK,
            )
            .all()
        )
        found = {}
        for row in rows:
            try:
                found[row.match_id] = NetstatsSummary.model_validate(row.summary)
            except ValidationError:
                logger.warning(
                    "stored netstats no longer validate", match_id=row.match_id
                )
        return found

    def matches_to_fetch(
        self, since: datetime, max_attempts: int, limit: int
    ) -> list[NetstatsWork]:
        """Matches played since ``since`` that haven't used up their fetches."""
        # Refetched even once found: players upload their logs at different times.
        rows = (
            self.session.query(
                Match.match_id, func.coalesce(MatchNetstatsRow.attempts, 0)
            )
            .outerjoin(MatchNetstatsRow, MatchNetstatsRow.match_id == Match.match_id)
            .filter(Match.timestamp >= since)
            .filter(
                MatchNetstatsRow.match_id.is_(None)
                | (MatchNetstatsRow.attempts < max_attempts)
            )
            .order_by(Match.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [NetstatsWork(*r) for r in rows]

    def stale_rows(self, parser_version: int, limit: int) -> list[NetstatsWork]:
        """Rows with logs archived that an older parser wrote."""
        rows = (
            self.session.query(MatchNetstatsRow.match_id, MatchNetstatsRow.attempts)
            .filter(
                MatchNetstatsRow.status.in_(
                    (NetstatsStatus.OK, NetstatsStatus.PARSE_ERROR)
                ),
                MatchNetstatsRow.parser_version < parser_version,
            )
            .limit(limit)
            .all()
        )
        return [NetstatsWork(*r) for r in rows]

    def delete_all(self) -> list[int]:
        """Drop every row; returns the match ids that had one."""
        ids = list(
            self.session.scalars(
                delete(MatchNetstatsRow).returning(MatchNetstatsRow.match_id)
            )
        )
        self._commit_if_auto()
        return ids

    def save(
        self,
        match_id: int,
        status: NetstatsStatus,
        parser_version: int,
        summary: NetstatsSummary | None,
        attempts: int,
    ) -> None:
        self.session.merge(
            MatchNetstatsRow(
                match_id=match_id,
                status=status,
                parser_version=parser_version,
                summary=summary.model_dump(mode="json") if summary else None,
                attempts=attempts,
                fetched_at=datetime.now(UTC),
            )
        )
        self._commit_if_auto()
