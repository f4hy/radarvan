"""Tournament registry, tournament-game links, and TournamentReport/TournamentStat."""

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..api_types import (
    Statistic as PydanticStatistic,
    TournamentReport as PydanticTournamentReport,
)
from ..db import Tournament, TournamentGame, TournamentReport, TournamentStat

from .base import BaseRepo


class TournamentRepo(BaseRepo):
    """Operations on Tournament, TournamentGame, TournamentReport + TournamentStat.

    The registry/link half lives here rather than in a new repo because
    ``TournamentRepo`` is already part of the ``ReplayManager`` facade, and
    ``matches.get_match_infos`` (which needs the links to tag every MatchInfo)
    only ever gets handed a ReplayManager.
    """

    # --- Tournament registry ---

    def list_tournaments(self) -> list[Tournament]:
        """Every tournament, newest first.

        Sorted on ``start_date`` where there is one and ``created_at``
        otherwise - a bracket carries no dates, so ordering on ``start_date``
        alone buried the running bracket under every finished round robin.
        """
        rows = list(self.session.scalars(select(Tournament)).all())
        rows.sort(key=lambda t: t.start_date or t.created_at.date(), reverse=True)
        return rows

    def get_tournament_by_slug(self, slug: str) -> Tournament | None:
        return self.session.scalar(select(Tournament).where(Tournament.slug == slug))

    def get_tournament_by_id(self, tournament_id: int) -> Tournament | None:
        return self.session.get(Tournament, tournament_id)

    def upsert_tournament(
        self,
        slug: str,
        name: str,
        tournament_format: str,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str = "active",
    ) -> Tournament:
        """Create the tournament, or update the mutable fields of an existing one.

        ``slug`` is the stable identity; everything else can be corrected later
        without orphaning the TournamentGame rows hanging off the row's id.
        """
        row = self.get_tournament_by_slug(slug)
        if row is None:
            row = Tournament(slug=slug)
            self.session.add(row)
        row.name = name
        row.format = tournament_format
        row.start_date = start_date
        row.end_date = end_date
        row.status = status
        self.session.flush()
        self._commit_if_auto()
        return row

    # --- Tournament game links ---

    def links_by_match(self) -> dict[int, TournamentGame]:
        """{match_id: link} for every linked match - one query, used to tag
        every MatchInfo in ``matches.get_match_infos``.

        Excluded rows are tombstones, not links, so they're left out here: a
        warmup game must not come back tagged as a tournament game.

        A match belongs to at most one tournament in practice (the unique
        index is per-tournament, so duplicates are possible but meaningless);
        the last row wins rather than raising, since a stray duplicate must
        not break the entire match listing.
        """
        stmt = (
            select(TournamentGame)
            .where(TournamentGame.excluded.is_(False))
            # match_to_matchinfo reads link.tournament.slug for every match;
            # without this the loader strategy is what decides whether that
            # costs one query or thousands.
            .options(selectinload(TournamentGame.tournament))
        )
        return {row.match_id: row for row in self.session.scalars(stmt).all()}

    def link_counts_by_slug(self) -> dict[str, int]:
        """{slug: linked game count} - an indexed aggregate over the link
        table, so listing tournaments doesn't have to touch the match cache."""
        stmt = (
            select(Tournament.slug, func.count(TournamentGame.id))
            .join(TournamentGame, TournamentGame.tournament_id == Tournament.id)
            .where(TournamentGame.excluded.is_(False))
            .group_by(Tournament.slug)
        )
        return dict(self.session.execute(stmt).all())  # type: ignore[arg-type]

    def list_links(
        self,
        tournament_id: int | None = None,
        stage: str | None = None,
        include_excluded: bool = False,
    ) -> list[TournamentGame]:
        """Links for a tournament (or all of them), tombstones omitted.

        ``include_excluded`` is for the admin UI, which needs to show what's
        been deliberately kept out so it can be put back.
        """
        stmt = select(TournamentGame)
        if not include_excluded:
            stmt = stmt.where(TournamentGame.excluded.is_(False))
        if tournament_id is not None:
            stmt = stmt.where(TournamentGame.tournament_id == tournament_id)
        if stage is not None:
            stmt = stmt.where(TournamentGame.stage == stage)
        stmt = stmt.order_by(TournamentGame.stage, TournamentGame.series_index)
        return list(self.session.scalars(stmt).all())

    def link_match(
        self,
        tournament_id: int,
        match_id: int,
        stage: str | None = None,
        round_name: str | None = None,
        series_index: int | None = None,
        source: str = "auto",
        excluded: bool = False,
    ) -> TournamentGame:
        """Link a match to a tournament, or update an existing link.

        An ``auto`` write never overwrites a ``manual`` row: manual links are
        an admin's explicit judgement (a warmup excluded, a mis-detected match
        corrected), and re-running the detector must not undo them. That guard
        is also what makes an exclusion stick - a tombstone is a manual row.
        """
        if source not in ("auto", "manual"):
            raise ValueError(f"Invalid link source {source!r}")
        row = self.session.scalar(
            select(TournamentGame).where(
                TournamentGame.tournament_id == tournament_id,
                TournamentGame.match_id == match_id,
            )
        )
        if row is None:
            row = TournamentGame(tournament_id=tournament_id, match_id=match_id)
            self.session.add(row)
        elif row.source == "manual" and source == "auto":
            return row
        row.stage = stage
        row.round_name = round_name
        row.series_index = series_index
        row.source = source
        row.excluded = excluded
        self.session.flush()
        self._commit_if_auto()
        return row

    def exclude_match(
        self, tournament_id: int, match_id: int, stage: str | None = None
    ) -> TournamentGame:
        """Mark a match as deliberately *not* a game of this tournament.

        Use instead of ``unlink_match`` whenever the detector would find the
        match again - a warmup between the two entrants on bracket night, a
        game replayed after a disconnect. Deleting only lasts until the next
        detector run; this lasts.

        Keeps whatever round/series the row already carried: the admin view
        exists to show what was kept out so it can be put back, which needs
        to say *where* it was.
        """
        existing = self.session.scalar(
            select(TournamentGame).where(
                TournamentGame.tournament_id == tournament_id,
                TournamentGame.match_id == match_id,
            )
        )
        return self.link_match(
            tournament_id,
            match_id,
            stage=stage
            if stage is not None
            else (existing.stage if existing else None),
            round_name=existing.round_name if existing else None,
            series_index=existing.series_index if existing else None,
            source="manual",
            excluded=True,
        )

    def unlink_match(self, tournament_id: int, match_id: int) -> bool:
        """Remove a link. Returns True if a row was deleted."""
        row = self.session.scalar(
            select(TournamentGame).where(
                TournamentGame.tournament_id == tournament_id,
                TournamentGame.match_id == match_id,
            )
        )
        if row is None:
            return False
        self.session.delete(row)
        self._commit_if_auto()
        return True

    # --- Reports ---

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
        self._commit_if_auto()

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
                date_computed=db_stat.date_computed or datetime.now(UTC).date(),
                value=value,
                player=db_stat.player,
                match_id=db_stat.match_id,
            )
            pydantic_stats.append(pydantic_stat)

        return PydanticTournamentReport(name=db_report.name, stats=pydantic_stats)
