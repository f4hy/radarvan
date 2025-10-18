"""Get match info from a replay."""

import datetime
from api_types import Matches, MatchInfo, Player, General, Team
from cncstats_types import EnhancedReplay, PlayerSummary, GeneralsHeader
import utils
import logging

logger = logging.getLogger(__name__)


def match_from_replay(replay: EnhancedReplay) -> MatchInfo | None:
    duration_minutes = utils.duration_minutes(replay)
    if duration_minutes < 2:
        logger.info("under 2 minutes, not a real game")
        return None
    _winners = [p for p in replay.Summary if p.Win is True]
    notes = ""
    if _winners:
        winner = _winners[0].Team
        incomplete = ""
        logger.info(f"\n winner {winner} \n")
        if winner == Team.NONE:
            logger.info(f"No winner found in replay {replay.Summary=}")
    if not _winners:
        winner = Team.NONE
        incomplete = "Likely Mismatch :("
    elif winner == Team.NONE:
        notes = "No team won?"
    # if winner == Team.OBSERVER:
    #     notes = ""

    color_map = {p.Name: p.Color for p in replay.Header.Metadata.Players}
    # wont be needed once cncstats fixes observers
    observers = {p.Name for p in replay.Header.Metadata.Players if p.Team == -1}
    players = [
        utils.player_summary_to_player(p, color_map, observers) for p in replay.Summary
    ]
    return MatchInfo(
        id=replay.Header.Metadata.Seed,
        timestamp=replay.Header.TimeStampBegin,
        map=replay.Header.Metadata.MapFile,
        winning_team=winner,
        players=players,
        duration_minutes=duration_minutes,
        filename=replay.Header.FileName,
        incomplete=incomplete,
        notes=notes,
    )
