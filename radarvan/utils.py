"""Shared logic about replay computing."""

import datetime
import threading
from collections.abc import Callable, MutableMapping
from typing import Any, cast
from zoneinfo import ZoneInfo
from cachetools import cached
from .api_types import Player, General, Team
from .cncstats_model.zhreplay import EnhancedReplayV2, PlayerSummaryV2
from .cncstats_model.header import Player as HeaderPlayer
from .player_role import (
    PlayerRole,
    normalize_color,
    role_from_header,
    start_position_from_header,
    team_from_header,
)
import structlog
import time
import functools

logger = structlog.get_logger(__name__)


def locked_cached[F: Callable[..., Any]](
    cache: MutableMapping[Any, Any], key: Callable[..., Any]
) -> Callable[[F], F]:
    """cachetools ``@cached`` with a dedicated lock baked in.

    cachetools caches are not thread-safe, and sync endpoints run in uvicorn's
    threadpool, so every process-global cache must be locked. Using this
    helper instead of a bare ``@cached`` makes the lock impossible to forget.
    (Caches that need ``cache_clear()`` coordination keep explicit locks in
    ``radarvan.cache``.)
    """
    return cast(Callable[[F], F], cached(cache=cache, key=key, lock=threading.Lock()))


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
    start = datetime.datetime.fromtimestamp(
        header.time_stamp_begin or 0, tz=datetime.UTC
    )
    end = datetime.datetime.fromtimestamp(header.time_stamp_end or 0, tz=datetime.UTC)
    return (end - start).total_seconds() / 60.0


# The community plays in US Eastern; the "game night" view groups late sessions
# onto the evening they started. We convert the match's UTC instant to Eastern
# (ZoneInfo handles the EST/EDT switch automatically) and roll the day boundary
# forward to ~5am local, so games played into the early morning (e.g. a Saturday
# night running to 1-2am Sunday) still count toward the night they began.
GAME_NIGHT_TZ = ZoneInfo("America/New_York")
_GAME_NIGHT_ROLLOVER_HOURS = 5


def game_night_date(timestamp: int | float) -> datetime.date:
    """Calendar date of the 'game night' a match belongs to.

    `timestamp` is the replay's `time_stamp_begin` - a POSIX (UTC) epoch.
    """
    instant = datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
    local = instant.astimezone(GAME_NIGHT_TZ)
    return (local - datetime.timedelta(hours=_GAME_NIGHT_ROLLOVER_HOURS)).date()


def game_night_date_of(when: datetime.datetime) -> datetime.date:
    """game_night_date for a datetime rather than a POSIX epoch.

    For instants that aren't replay timestamps - e.g. a bracket match's
    scheduled_at. A naive value is read as UTC, matching how every stored
    timestamp in this app is written. Anything comparing against
    ``MatchInfo.date`` must go through this, not ``.date()``: an 8pm Eastern
    match is already the *next* UTC day, so a raw UTC date lands on a game
    night that has no games in it.
    """
    instant = when if when.tzinfo else when.replace(tzinfo=datetime.UTC)
    return game_night_date(instant.timestamp())


def minutes_per_step(replay: EnhancedReplayV2) -> float:
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


def is_observer(player_header: HeaderPlayer) -> bool:
    """True for a spectator slot rather than an actual competitor."""
    return role_from_header(player_header) == PlayerRole.OBSERVER


def is_competitor(player_header: HeaderPlayer) -> bool:
    """True for a header slot that actually plays the game.

    Spectators come through as type "H" like everyone else, so the H/C check
    alone does not exclude them - a 1v1 watched by two spectators looks like
    a four-player game without this.
    """
    return not is_observer(player_header)


def determine_team(
    player_header: HeaderPlayer, player_summary: PlayerSummaryV2 | None
) -> Team:
    return Team(team_from_header(player_header))


def determine_general(
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
        color = normalize_color(p.color)
        summary = summaries_by_name.get(p.name) or summaries_by_index.get(i)
        team = determine_team(p, player_summary=summary)
        faction = determine_general(p, player_summary=summary)
        starting_position = start_position_from_header(p)
        players.append(
            Player(
                name=p.name or (summary.name if summary else "") or "CPU",
                general=faction,
                team=team,
                role=role_from_header(p),
                color=color,
                won=summary.win if summary else False,
                starting_position=starting_position,
            )
        )
    return players
