"""Shared logic about replay computing."""

import datetime
from api_types import Matches, MatchInfo, Player, General, Team
from cncstats_types import EnhancedReplay, PlayerSummary
import logging

logger = logging.getLogger(__name__)


def duration_minutes(replay: EnhancedReplay) -> float:
    start = datetime.datetime.fromtimestamp(replay.Header.TimeStampBegin)
    end = datetime.datetime.fromtimestamp(replay.Header.TimeStampEnd)
    return (end - start).total_seconds() / 60.0


def side_to_general(side: str) -> General:
    match side:
        case "USA":
            return General.AIR
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
