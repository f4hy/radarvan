"""Get match info from a replay."""

from api_types import Matches, MatchInfo, Player, General, Team
from cncstats_types import EnhancedReplay, PlayerSummary
import logging

logger = logging.getLogger(__name__)


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


def player_summary_to_player(p: PlayerSummary) -> Player:
    return Player(
        name=p.Name or "Hard army?", general=side_to_general(p.Side), team=p.Team
    )


def match_from_replay(replay: EnhancedReplay) -> MatchInfo:
    winner = next(p for p in replay.Summary if p.Win == True).Team

    players = [player_summary_to_player(p) for p in replay.Summary]

    return MatchInfo(
        id=replay.Header.Metadata.Seed,
        timestamp=replay.Header.TimeStampBegin,
        map=replay.Header.Metadata.MapFile,
        winning_team=winner,
        players=players,
        duration_minutes=1.0,
        filename=replay.Header.Metadata.MapFile,
        incomplete="",
        notes="",
    )
