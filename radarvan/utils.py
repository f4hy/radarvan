"""Shared logic about replay computing."""

import datetime
from collections.abc import Callable
from typing import Any, cast
from .api_types import Player, General, Team
from .cncstats_types import EnhancedReplay, PlayerSummary, Player as HeaderPlayer
import logging
import time
import functools

logger = logging.getLogger(__name__)


def log_duration[F: Callable[..., Any]](func: F) -> F:
    """
    A decorator that logs the execution duration of the decorated function.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Function '{func.__name__}' executed in {duration:.4f} seconds.")
        return result

    return cast(F, wrapper)


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


def cncstats_faction_to_general(side: int) -> General:
    match side:
        case -2:
            return General.UNRECOGNIZED
        case -1:
            return General.UNRECOGNIZED
        case 2:
            return General.USA
        case 3:
            return General.CHINA
        case 4:
            return General.GLA
        case 5:
            return General.SUPER
        case 6:
            return General.LASER
        case 7:
            return General.AIR
        case 8:
            return General.TANK
        case 9:
            return General.INFANTRY
        case 10:
            return General.NUKE
        case 11:
            return General.TOXIN
        case 12:
            return General.DEMO
        case 13:
            return General.STEALTH
    raise ValueError(f"Unknown side {side=}")


def determine_team(
    player_header: HeaderPlayer, player_summary: PlayerSummary | None
) -> Team:
    if player_header.Faction == -2:
        return Team(Team.OBSERVER)
    if player_header.Team < 0:
        return Team(Team.NONE)
    return Team(player_header.Team + 1)


def determin_general(
    player_header: HeaderPlayer, player_summary: PlayerSummary | None
) -> General:
    faction = cncstats_faction_to_general(player_header.Faction)
    if faction == General.UNRECOGNIZED:
        # try the summary
        if player_summary:
            faction = side_to_general(player_summary.Side)
    return faction


def players_from_replay(replay: EnhancedReplay) -> list[Player]:
    players: list[Player] = []
    summaries = {s.Name: s for s in replay.Summary}
    for p in replay.Header.Metadata.Players:
        logger.info(f"Player {p=}")
        color = p.Color.lower().replace("color", "")
        team = determine_team(p, player_summary=summaries.get(p.Name))
        faction = determin_general(p, player_summary=summaries.get(p.Name))
        players.append(
            Player(
                name=p.Name or "CPU",
                general=faction,
                team=team,
                color=color,
            )
        )
    return players
