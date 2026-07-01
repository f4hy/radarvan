"""Per-entity database repositories.

Each repo class encapsulates operations on one entity (or a tightly coupled
cluster). Repos can be instantiated standalone with a Session, or composed
together via the `ReplayManager` facade in `radarvan.db_utils`.
"""

from .base import BaseRepo
from .bracket import BracketRepo
from .details import MatchDetailsRepo
from .maps import MapRepo
from .matches import MatchDebugData, MatchRepo
from .replays import AllFilesForId, FileListing, ReplayRepo, ReplayToProcess
from .stats import StatsRepo
from .tournaments import TournamentRepo
from .users import UserRepo
from .votes import MapVoteRepo, VoteLimitExceeded

__all__ = [
    "AllFilesForId",
    "BaseRepo",
    "BracketRepo",
    "FileListing",
    "MapRepo",
    "MapVoteRepo",
    "MatchDebugData",
    "MatchDetailsRepo",
    "MatchRepo",
    "ReplayRepo",
    "ReplayToProcess",
    "StatsRepo",
    "TournamentRepo",
    "UserRepo",
    "VoteLimitExceeded",
]
