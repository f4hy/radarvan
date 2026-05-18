"""ComputedStatistic repository (pre-baked superlatives)."""

from datetime import date

from sqlalchemy import delete as sa_delete, func, select

from ..api_types import Statistic as PydanticStatistic
from ..db import ComputedStatistic

from .base import BaseRepo


class StatsRepo(BaseRepo):
    """Operations on ComputedStatistic."""

    def clear_computed_stats(self) -> int:
        """Delete all computed statistics. Returns the number of rows deleted."""
        result = self.session.execute(sa_delete(ComputedStatistic))
        self._commit_if_auto()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]

    def save_computed_stats(self, stats: list[PydanticStatistic]) -> None:
        """Persist a batch of computed statistics using each stat's date_computed."""
        for stat in stats:
            db_stat = ComputedStatistic(
                stat_name=stat.stat_name,
                player=stat.player,
                match_id=stat.match_id,
                date_computed=stat.date_computed,
            )
            if stat.value is not None:
                if isinstance(stat.value, (int, float)):
                    db_stat.value_float = float(stat.value)
                else:
                    db_stat.value_str = str(stat.value)
            self.session.add(db_stat)
        self._commit_if_auto()

    def get_computed_stats(self) -> list[PydanticStatistic]:
        """Return all persisted computed statistics, ordered by id."""
        stmt = select(ComputedStatistic).order_by(ComputedStatistic.id)
        rows = list(self.session.scalars(stmt).all())
        return [
            PydanticStatistic(
                stat_name=row.stat_name,
                date_computed=row.date_computed,
                value=row.value_float if row.value_float is not None else row.value_str,
                player=row.player,
                match_id=row.match_id,
            )
            for row in rows
        ]

    def computed_stats_are_stale(self, days: int = 3) -> bool:
        """Return True if no computed stats exist or the newest is older than `days` days."""
        latest = self.session.scalar(select(func.max(ComputedStatistic.date_computed)))
        if latest is None:
            return True
        return (date.today() - latest).days > days
