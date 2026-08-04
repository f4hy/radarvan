"""Match repository.

Owns: Match, MatchPlayer, MatchCompostion, WinnerOverride. These are tightly
coupled: composition is keyed on match_id; overrides override match winner
fields; reset_match deletes across all four.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
import structlog

from sqlalchemy import or_, select, func
from sqlalchemy.exc import IntegrityError

from ..db import (
    Match,
    MatchCompostion,
    MatchPlayer,
    ParsedReplayJson,
    ProcessingStatus,
    ReplayFile,
    WinnerOverride,
)
from ..game_composition import GameComposition, compute_match_composition
from ..notify import notify

from .base import BaseRepo

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MatchDebugData:
    matches: Match | None
    match_players: list[MatchPlayer]
    match_compostion: MatchCompostion | None
    winner_overrides: WinnerOverride | None
    parsed_replay_json: list[ParsedReplayJson]
    replay_files: list[ReplayFile]


class MatchRepo(BaseRepo):
    """Operations on Match, MatchPlayer, MatchCompostion, and WinnerOverride."""

    # --- Match ---

    def latest_match_created_at(self) -> datetime | None:
        return self.session.scalar(select(func.max(Match.created_at)))

    def get_match(self, match_id: int) -> Match | None:
        return self.session.get(Match, match_id)

    def register_match(self, db_match: Match) -> tuple[Match, bool]:
        """Insert a new Match; return (match, created).

        created is False when a match with this match_id already exists,
        including when a concurrent request inserts it between our existence
        check and the commit (both players' clients upload the same match at
        game end, so this races routinely).
        """
        logger.info("registering match", match=db_match)
        existing = self.session.get(Match, db_match.match_id)
        if existing is not None:
            logger.warning("match already exists", match_id=db_match.match_id)
            return existing, False
        self.session.add(db_match)
        try:
            self.session.flush()
            self._commit_if_auto()
        except IntegrityError:
            self.session.rollback()
            existing = self.session.get(Match, db_match.match_id)
            if existing is None:
                raise
            logger.warning("match registered concurrently", match_id=db_match.match_id)
            return existing, False
        if self.notify:
            notify(f"Registered Match {db_match}")
        return db_match, True

    def update_match(self, new_match: Match) -> Match | None:
        """Replace the existing match record with data from new_match."""
        existing = self.session.get(Match, new_match.match_id)
        if existing is None:
            return None
        if (
            new_match.winning_team_id is not None
            and existing.winning_team_id != new_match.winning_team_id
        ):
            notify(
                f"Update to Match id {new_match.match_id} is changing the winner"
                f" from {existing.winning_team_id} to {new_match.winning_team_id}"
            )
        # Preserve the original creation timestamp since new_match won't have it set.
        new_match.created_at = existing.created_at
        # Preserve is_dev: it comes from the upload header, not the replay, so a
        # reparse-built match always has the default False and would clobber it.
        new_match.is_dev = existing.is_dev
        # merge() copies attribute state by PK, so an unset onupdate column
        # merges as NULL instead of firing onupdate=func.now() - set explicitly.
        new_match.updated_at = datetime.now(UTC)
        # Clear players before merge: new MatchPlayer objects have no id, so merge
        # would insert duplicates rather than replace the existing rows.
        existing.players.clear()
        self.session.flush()
        merged = self.session.merge(new_match)
        self._commit_if_auto()
        if self.notify:
            notify(f"Update Match {merged}")
        return merged

    def list_matches(self, duration_cutoff: float) -> list[Match]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Match)
            .where(Match.duration_minutes > duration_cutoff)
            .options(selectinload(Match.composition))
            .options(selectinload(Match.players))
            .options(selectinload(Match.replay_json))
        )
        return list(self.session.scalars(stmt).all())

    def list_matches_with_winner_but_incomplete(
        self, limit: int = 10
    ) -> list[tuple[Match, bool | None]]:
        stmt = (
            select(Match, ParsedReplayJson.has_enhanced_stats)
            .join(Match.replay_json)
            .where(
                Match.incomplete.isnot(None),
                Match.incomplete != "",
                Match.incomplete != "Too Short",
                Match.winning_team_id > 0,
            )
            .limit(limit)
        )
        # Row[tuple[...]] is a tuple subclass at runtime but SQLAlchemy stubs
        # don't express this, so the Sequence[Row[...]] → list[tuple[...]] conversion
        # isn't accepted without an ignore.
        return list(self.session.execute(stmt).all())  # type: ignore[arg-type]

    def list_matches_with_player_unk(self, limit: int = 10) -> list[int]:
        stmt = (
            select(MatchPlayer.match_id)
            .where(
                MatchPlayer.general_id < 0,
                MatchPlayer.team_id > 0,
            )
            .limit(limit)
            .distinct()
        )
        return list(self.session.scalars(stmt).all())

    def list_matches_without_composition(self) -> Iterator[int]:
        """Yield match_ids for matches with no MatchCompostion row or an Unknown category."""
        stmt = (
            select(Match.match_id)
            .outerjoin(MatchCompostion, MatchCompostion.match_id == Match.match_id)
            .where(
                or_(
                    MatchCompostion.match_id.is_(None),
                    MatchCompostion.category == "Unknown",
                )
            )
        )
        yield from self.session.scalars(stmt).all()

    # --- MatchCompostion ---

    def compute_and_save_composition(self, match_id: int) -> GameComposition | None:
        """Compute match composition from MatchPlayer rows and persist."""
        match = self.session.get(Match, match_id)
        if match is None:
            return None
        comp = compute_match_composition(match.players)
        db_comp = MatchCompostion(
            match_id=match_id,
            category=comp.category,
            is_comp_stomp=comp.is_comp_stomp,
            is_ffa=comp.is_ffa,
            num_teams=comp.num_teams,
            team_sizes=comp.team_sizes,
            total_players=comp.total_players,
            num_humans=comp.num_humans,
            num_computers=comp.num_computers,
            is_balanced=comp.is_balanced,
            is_1v1=comp.is_1v1,
            is_team_game=comp.is_team_game,
        )
        self.session.merge(db_comp)
        self._commit_if_auto()
        return comp

    # --- WinnerOverride ---

    def get_overrides(self) -> dict[int, WinnerOverride]:
        """Get winner overrides."""
        stmt = select(WinnerOverride)
        overrides = self.session.execute(stmt).scalars().all()
        return {o.match_id: o for o in overrides}

    def set_override(
        self, match_id: int, winner: int | None, incomplete: str | None = None
    ) -> WinnerOverride:
        """Set winner and/or incomplete override for a match."""
        logger.info(
            "setting override", match_id=match_id, winner=winner, incomplete=incomplete
        )

        existing = self.session.get(WinnerOverride, match_id)
        new_override = WinnerOverride(
            match_id=match_id,
            winning_team_id=winner
            if winner is not None
            else (existing.winning_team_id if existing else None),
            incomplete=incomplete
            if incomplete is not None
            else (existing.incomplete if existing else None),
        )

        self.session.merge(new_override)
        self._commit_if_auto()
        if self.notify:
            notify(f"Saved override {new_override}")
        return new_override

    def delete_override(self, match_id: int) -> bool:
        """Delete a winner override. Returns True if deleted, False if not found."""
        override = self.session.get(WinnerOverride, match_id)
        if override is None:
            return False
        self.session.delete(override)
        self._commit_if_auto()
        return True

    # --- Cross-entity ---

    def reset_match(self, match_id: int) -> dict[str, int]:
        """Delete all data for a match except the ReplayFile; reset ReplayFile status to PENDING.

        Deletion order respects FK constraints:
          1. WinnerOverride (no FK dependency)
          2. MatchCompostion (FK → matches, deleted before Match)
          3. Match (ORM cascade deletes MatchPlayers)
          4. ParsedReplayJson (FK ← Match now gone)
          5. ReplayFile status reset to PENDING
        """
        counts: dict[str, int] = {
            "winner_overrides": 0,
            "match_composition": 0,
            "match": 0,
            "parsed_replay_json": 0,
            "replay_files_reset": 0,
        }

        override = self.session.get(WinnerOverride, match_id)
        if override:
            self.session.delete(override)
            counts["winner_overrides"] = 1

        composition = self.session.get(MatchCompostion, match_id)
        if composition:
            self.session.delete(composition)
            counts["match_composition"] = 1

        match = self.session.get(Match, match_id)
        if match:
            self.session.delete(match)
            counts["match"] = 1

        # Flush so the Match delete is visible before we touch ParsedReplayJson
        self.session.flush()

        parsed_jsons = list(
            self.session.scalars(
                select(ParsedReplayJson).where(ParsedReplayJson.match_id == match_id)
            ).all()
        )
        replay_file_urls = [p.replay_file_url for p in parsed_jsons]
        for p in parsed_jsons:
            self.session.delete(p)
        counts["parsed_replay_json"] = len(parsed_jsons)

        self.session.flush()

        replay_files_to_reset = list(
            self.session.scalars(
                select(ReplayFile).where(ReplayFile.original_url.in_(replay_file_urls))
            ).all()
        )
        for rf in replay_files_to_reset:
            rf.status = ProcessingStatus.PENDING
            counts["replay_files_reset"] += 1

        self._commit_if_auto()
        return counts

    def get_all_data_for_match(self, match_id: int) -> MatchDebugData:
        """Fetch every row related to a match_id across all tables."""
        match = self.session.get(Match, match_id)
        players = list(
            self.session.scalars(
                select(MatchPlayer).where(MatchPlayer.match_id == match_id)
            ).all()
        )
        composition = self.session.get(MatchCompostion, match_id)
        override = self.session.get(WinnerOverride, match_id)
        parsed_jsons = list(
            self.session.scalars(
                select(ParsedReplayJson).where(ParsedReplayJson.match_id == match_id)
            ).all()
        )
        replay_file_urls = [p.replay_file_url for p in parsed_jsons]
        replay_files = (
            list(
                self.session.scalars(
                    select(ReplayFile).where(
                        ReplayFile.original_url.in_(replay_file_urls)
                    )
                ).all()
            )
            if replay_file_urls
            else []
        )
        return MatchDebugData(
            matches=match,
            match_players=players,
            match_compostion=composition,
            winner_overrides=override,
            parsed_replay_json=parsed_jsons,
            replay_files=replay_files,
        )
