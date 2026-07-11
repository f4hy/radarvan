"""Database manager and the ReplayManager facade.

ReplayManager is a multiple-inheritance composition of the per-entity
repositories in `radarvan.repositories`. New code should prefer instantiating
the specific repo it needs (e.g. `MatchRepo(session)`) over taking a fat
ReplayManager dependency. ReplayManager remains for backwards compatibility
with the many existing callers.
"""

from collections.abc import Generator
from contextlib import contextmanager
import structlog

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .db import Base
from .repositories import (
    AllFilesForId,
    FileListing,
    MapRepo,
    MatchDebugData,
    MatchDetailsRepo,
    MatchRepo,
    ProfileRepo,
    ReplayRepo,
    ReplayToProcess,
    StatsRepo,
    TournamentRepo,
)

logger = structlog.get_logger(__name__)


__all__ = [
    "AllFilesForId",
    "DatabaseManager",
    "FileListing",
    "MatchDebugData",
    "ReplayManager",
    "ReplayToProcess",
]


class DatabaseManager:
    def __init__(self, connection_string: str):
        """Initialize a process-wide database engine + sessionmaker.

        Example: DatabaseManager('postgresql://user:password@localhost:5432/cnc_stats')
        """
        con_str = connection_string.replace("postgres://", "postgresql://")
        self.engine = create_engine(con_str, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_all_tables(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session]:
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def get_replay_manager(self, notify: bool = False) -> Generator["ReplayManager"]:
        with self.get_session() as session:
            yield ReplayManager(session, notify=notify)


class ReplayManager(
    MatchRepo,
    ReplayRepo,
    MapRepo,
    StatsRepo,
    TournamentRepo,
    MatchDetailsRepo,
    ProfileRepo,
):
    """Facade over every per-entity repository.

    Method resolution: each method lives on exactly one parent repo, so there
    are no MRO ambiguities. The facade adds no new behavior - it exists so
    legacy callers can keep using a single object that does everything.
    """
