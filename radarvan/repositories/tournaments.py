"""TournamentReport / TournamentStat repository."""

from datetime import date

from sqlalchemy import select

from ..api_types import (
    Statistic as PydanticStatistic,
    TournamentReport as PydanticTournamentReport,
)
from ..db import TournamentReport, TournamentStat

from .base import BaseRepo


class TournamentRepo(BaseRepo):
    """Operations on TournamentReport + TournamentStat."""

    def save_tournament_report(
        self,
        pydantic_report: PydanticTournamentReport,
    ) -> None:
        """Persist a Pydantic TournamentReport, replacing any existing report of the same name."""
        stmt = select(TournamentReport).where(
            TournamentReport.name == pydantic_report.name
        )
        db_report = self.session.scalar(stmt)
        if db_report is not None:
            # Update existing report - remove old stats
            db_report.stats.clear()
        else:
            db_report = TournamentReport(name=pydantic_report.name)

        for pydantic_stat in pydantic_report.stats:
            db_stat = TournamentStat(
                stat_name=pydantic_stat.stat_name,
                player=pydantic_stat.player,
                match_id=pydantic_stat.match_id,
                date_computed=pydantic_stat.date_computed,
                tournament_report=db_report,
            )

            if pydantic_stat.value is not None:
                if isinstance(pydantic_stat.value, (int, float)):
                    db_stat.value_float = float(pydantic_stat.value)
                else:
                    db_stat.value_str = str(pydantic_stat.value)

        self.session.add(db_report)
        self.session.commit()

    def get_tournament_report_by_name(
        self, name: str
    ) -> PydanticTournamentReport | None:
        """Retrieve a TournamentReport by name and convert to the Pydantic shape."""
        stmt = select(TournamentReport).where(TournamentReport.name == name)
        db_report = self.session.scalar(stmt)

        if db_report is None:
            return None

        pydantic_stats = []
        for db_stat in db_report.stats:
            value = (
                db_stat.value_float
                if db_stat.value_float is not None
                else db_stat.value_str
            )

            pydantic_stat = PydanticStatistic(
                stat_name=db_stat.stat_name,
                date_computed=db_stat.date_computed or date.today(),
                value=value,
                player=db_stat.player,
                match_id=db_stat.match_id,
            )
            pydantic_stats.append(pydantic_stat)

        return PydanticTournamentReport(name=db_report.name, stats=pydantic_stats)
