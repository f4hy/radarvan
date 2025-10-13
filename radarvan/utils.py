"""Shared logic about replay computing."""

import datetime
from api_types import Matches, MatchInfo, Player, General, Team
from cncstats_types import EnhancedReplay, PlayerSummary
import logging

logger = logging.getLogger(__name__)


def duration_minutes(replay: EnhancedReplay) -> float:
    start = datetime.datetime.fromtimestamp(replay.Header.TimeStampBegin)
    end = datetime.datetime.fromtimestamp(replay.Header.TimeStampEnd)
    return (end - start).total_seconds() / 60.

# def minute_per_timestep(replay: EnhancedReplay) -> float:
#     """Get the minute per timestep for this replay."""
#     minutes = duration_minutes(replay)
#     last_timecode = replay.Body[-1]
#     return minutes /
