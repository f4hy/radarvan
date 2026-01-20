"""Shared logic about replay computing."""

import datetime
from api_types import Player, General, Team
from cncstats_types import EnhancedReplay, PlayerSummary
import logging
import time
import functools

logger = logging.getLogger(__name__)


def log_duration(func):
    """
    A decorator that logs the execution duration of the decorated function.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Function '{func.__name__}' executed in {duration:.4f} seconds.")
        return result

    return wrapper


def duration_minutes(replay: EnhancedReplay) -> float:
    start = datetime.datetime.fromtimestamp(replay.Header.TimeStampBegin)
    end = datetime.datetime.fromtimestamp(replay.Header.TimeStampEnd)
    return (end - start).total_seconds() / 60.0


def minutess_per_step(replay: EnhancedReplay) -> float:
    """Scale factor to convert a timecode to minutes."""
    minutes = duration_minutes(replay)
    stamps = replay.Header.NumTimeStamps
    return minutes / stamps


def side_to_general(side: str) -> General:
    match side:
        case "USA":
            return General.USA
        case "USA Airforce":
            return General.AIR
        case "USA Lazr":
            return General.LASER
        case "USA Superweapon":
            return General.SUPER
        case "China":
            return General.CHINA
        case "China Nuke":
            return General.NUKE
        case "China Tank":
            return General.TANK
        case "China Infantry":
            return General.INFANTRY
        case "GLA":
            return General.GLA
        case "GLA Toxin":
            return General.TOXIN
        case "GLA Stealth":
            return General.STEALTH
        case "GLA Demo":
            return General.DEMO
        case "":
            return General.UNRECOGNIZED
    logger.warning(f"Unknown side {side=}")
    return General.UNRECOGNIZED


def player_summary_to_player(
    p: PlayerSummary, color_map: dict[str, str], observers: set[str]
) -> Player:
    color = color_map.get(p.Name, "black").lower().replace("color", "")
    team = Team.OBSERVER if p.Name in observers else p.Team
    if not p.Name:
        color = "grey"
    return Player(
        name=p.Name or "CPU",
        general=side_to_general(p.Side),
        team=team,
        color=color,
    )


# def minute_per_timestep(replay: EnhancedReplay) -> float:
#     """Get the minute per timestep for this replay."""
#     minutes = duration_minutes(replay)
#     last_timecode = replay.Body[-1]
#     return minutes /
