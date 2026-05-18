"""Per-entity database repositories.

Each repo class encapsulates operations on one entity (or a tightly coupled
cluster). Repos can be instantiated standalone with a Session, or composed
together via the `ReplayManager` facade in `radarvan.db_utils`.
"""

from .base import BaseRepo
from .maps import MapRepo
from .matches import MatchDebugData, MatchRepo
from .replays import AllFilesForId, FileListing, ReplayRepo, ReplayToProcess
from .stats import StatsRepo
from .tournaments import TournamentRepo

__all__ = [
    "AllFilesForId",
    "BaseRepo",
    "FileListing",
    "MapRepo",
    "MatchDebugData",
    "MatchRepo",
    "ReplayRepo",
    "ReplayToProcess",
    "StatsRepo",
    "TournamentRepo",
]
