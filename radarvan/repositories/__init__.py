"""Per-entity database repositories.

Each repo class encapsulates operations on one entity (or a tightly coupled
cluster). Repos can be instantiated standalone with a Session, or composed
together via the `ReplayManager` facade in `radarvan.db_utils`.
"""

from .base import BaseRepo
from .bracket import BracketRepo
from .bracket_predictions import BracketPredictionRepo
from .commentary import (
    BracketSummaryRepo,
    GameNightSummaryRepo,
    MatchBlurbRepo,
    MatchupCommentaryRepo,
)
from .details import MatchDetailsRepo
from .maps import MapRepo
from .netstats import NetstatsRepo, StoredNetstats
from .matches import MatchDebugData, MatchRepo
from .profiles import ProfileRepo
from .replays import AllFilesForId, FileListing, ReplayRepo, ReplayToProcess
from .stats import StatsRepo
from .tournaments import TournamentRepo
from .users import UserRepo
from .votes import MapVoteRepo, VoteLimitExceeded

__all__ = [
    "AllFilesForId",
    "BaseRepo",
    "BracketPredictionRepo",
    "BracketRepo",
    "BracketSummaryRepo",
    "FileListing",
    "GameNightSummaryRepo",
    "MapRepo",
    "MapVoteRepo",
    "MatchBlurbRepo",
    "MatchDebugData",
    "MatchDetailsRepo",
    "MatchRepo",
    "MatchupCommentaryRepo",
    "NetstatsRepo",
    "ProfileRepo",
    "ReplayRepo",
    "ReplayToProcess",
    "StatsRepo",
    "StoredNetstats",
    "TournamentRepo",
    "UserRepo",
    "VoteLimitExceeded",
]
