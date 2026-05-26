"""Shared logic about replay computing."""

import datetime
from collections.abc import Callable
from typing import Any, cast
from .api_types import Player, General, Team
from .cncstats_model.zhreplay import EnhancedReplayV2, PlayerSummaryV2
from .cncstats_model.header import Player as HeaderPlayer
import structlog
import time
import functools

logger = structlog.get_logger(__name__)


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
        logger.debug(
            "function executed", function=func.__name__, duration_s=round(duration, 4)
        )
        return result

    return cast(F, wrapper)


def duration_minutes(replay: EnhancedReplayV2) -> float:
    header = replay.header
    start = datetime.datetime.fromtimestamp(header.time_stamp_begin or 0)
    end = datetime.datetime.fromtimestamp(header.time_stamp_end or 0)
    return (end - start).total_seconds() / 60.0


def minutess_per_step(replay: EnhancedReplayV2) -> float:
    """Scale factor to convert a timecode to minutes."""
    minutes = duration_minutes(replay)
    stamps = (replay.header.frame_count if replay.header else None) or 1
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
    logger.warning("unknown side", side=side)
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
    player_header: HeaderPlayer, player_summary: PlayerSummaryV2 | None
) -> Team:
    if player_header.type not in ("H", "C"):
        return Team(Team.OBSERVER)
    team_num = int(player_header.team or "-1")
    if team_num < 0:
        return Team(Team.NONE)
    return Team(team_num + 1)


def determin_general(
    player_header: HeaderPlayer, player_summary: PlayerSummaryV2 | None
) -> General:
    if player_summary:
        return side_to_general(player_summary.side or "")
    return General.UNRECOGNIZED


def players_from_replay(replay: EnhancedReplayV2) -> list[Player]:
    players: list[Player] = []
    summaries_by_name = {s.name: s for s in (replay.summary or []) if s.name}
    summaries_by_index = dict(enumerate(replay.summary or []))
    header_players = (
        replay.header.metadata.players
        if replay.header and replay.header.metadata
        else None
    ) or []
    for i, p in enumerate(header_players):
        color = (p.color or "").lower().replace("color", "")
        summary = summaries_by_name.get(p.name) or summaries_by_index.get(i)
        team = determine_team(p, player_summary=summary)
        faction = determin_general(p, player_summary=summary)
        try:
            # indexed from 0 in the replay
            starting_position = int(p.starting_position or "") + 1
        except (ValueError, TypeError):
            starting_position = None
        players.append(
            Player(
                name=p.name or (summary.name if summary else "") or "CPU",
                general=faction,
                team=team,
                color=color,
                won=summary.win if summary else False,
                starting_position=starting_position,
            )
        )
    return players
