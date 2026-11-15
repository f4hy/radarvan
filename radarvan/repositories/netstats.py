"""Operations on MatchNetstatsRow."""

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import NamedTuple

import structlog
from pydantic import ValidationError

from ..api_types import NetstatsSummary
from ..db import Match, MatchNetstatsRow
from .base import BaseRepo

logger = structlog.get_logger(__name__)

OK = "ok"
NO_LOGS = "no_logs"
PARSE_ERROR = "parse_error"


class StoredNetstats(NamedTuple):
    match_id: int
    summary: NetstatsSummary


class NetstatsRepo(BaseRepo):
    def get_summaries(self, match_ids: Iterable[int]) -> list[StoredNetstats]:
        """Stored summaries for ``match_ids``; a row that no longer validates is skipped."""
        ids = list(match_ids)
        if not ids:
            return []
        rows = (
            self.session.query(MatchNetstatsRow.match_id, MatchNetstatsRow.summary)
            .filter(MatchNetstatsRow.match_id.in_(ids), MatchNetstatsRow.status == OK)
            .all()
        )
        found = []
        for row in rows:
            try:
                summary = NetstatsSummary.model_validate(row.summary)
            except ValidationError:
                logger.warning(
                    "stored netstats no longer validate", match_id=row.match_id
                )
                continue
            found.append(StoredNetstats(row.match_id, summary))
        return found

    def attempts(self, match_id: int) -> int:
        row = self.session.get(MatchNetstatsRow, match_id)
        return row.attempts if row else 0

    def matches_to_fetch(
        self, since: datetime, max_attempts: int, limit: int
    ) -> list[int]:
        """Matches played since ``since`` that haven't used up their fetches."""
        # Refetched even once found: players upload their logs at different times.
        rows = (
            self.session.query(Match.match_id)
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
        return [r.match_id for r in rows]

    def stale_rows(self, parser_version: int, limit: int) -> list[int]:
        """Rows with logs on hand that an older parser wrote."""
        rows = (
            self.session.query(MatchNetstatsRow.match_id)
            .filter(
                MatchNetstatsRow.status.in_((OK, PARSE_ERROR)),
                MatchNetstatsRow.parser_version < parser_version,
            )
            .limit(limit)
            .all()
        )
        return [r.match_id for r in rows]

    def save(
        self,
        match_id: int,
        status: str,
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
