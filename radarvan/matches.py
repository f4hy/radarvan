"""Get match info from a replay."""

from collections.abc import Iterator
from log_time import log_time
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import db
import replay_files
import utils
from api_types import General, MatchInfo, Player, Team
from cncstats_types import EnhancedReplay
from db_utils import DatabaseManager, ReplayManager

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
        id=replay.replay_id(),
        timestamp=replay.Header.TimeStampBegin,
        map=replay.Header.Metadata.MapFile,
        winning_team=winner,
        players=players,
        duration_minutes=duration_minutes,
        filename=replay.Header.FileName,
        incomplete=incomplete,
        notes=notes,
    )


@utils.log_duration
def replay_to_db_match(replay: EnhancedReplay, json_s3_uri: str) -> db.Match:
    """replay to match."""
    match_id = replay.replay_id()
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
    color_map = {p.Name: p.Color for p in replay.Header.Metadata.Players}
    # wont be needed once cncstats fixes observers
    observers = {p.Name for p in replay.Header.Metadata.Players if p.Team == -1}
    players = [
        utils.player_summary_to_player(p, color_map, observers) for p in replay.Summary
    ]
    db_players = [
        db.MatchPlayer(
            match_id=match_id,
            player_name=p.name,
            general_id=p.general,
            team_id=p.team,
            color=p.color,
            is_winner=p.team == winner,
        )
        for p in players
    ]

    return db.Match(
        match_id=match_id,
        json_s3_uri=json_s3_uri,
        timestamp=datetime.fromtimestamp(replay.Header.TimeStampBegin),
        map=replay.Header.Metadata.MapFile,
        winning_team_id=winner,
        players=db_players,
        duration_minutes=utils.duration_minutes(replay),
        filename=replay.Header.FileName,
        incomplete=incomplete,
        notes=notes,
    )


def match_to_matchinfo(db_match: db.Match) -> MatchInfo:
    """Convert."""
    db_players = db_match.players
    players = [
        Player(
            name=p.player_name,
            general=p.general_id,
            team=p.team_id,
            color=p.color,
        )
        for p in db_players
    ]
    return MatchInfo(
        id=db_match.match_id,
        timestamp=db_match.timestamp,
        map=db_match.map,
        winning_team=db_match.winning_team_id,
        players=players,
        duration_minutes=db_match.duration_minutes,
        filename=db_match.json_s3_uri,
        incomplete=db_match.incomplete,
        notes=db_match.notes,
    )


def get_all_matches(replay_manager: ReplayManager) -> Iterator[MatchInfo]:
    replay_jsons = replay_manager.list_jsons(distinct=True)
    for j in replay_jsons:
        db_match = j.match
        if (db_match) is None:
            logger.info(f"Match was None, going to parse {j.replay_file_url}")
            parsed = replay_files.parse_replay(j.replay_file_url, replay_manager)
            db_match = replay_to_db_match(parsed, json_s3_uri=j.json_s3_uri)
            replay_manager.register_match(db_match)
        converted = match_to_matchinfo(db_match)
        if converted.duration_minutes < 2:
            continue
        yield converted


def register_matches(replay_manager: ReplayManager) -> Iterator[MatchInfo]:
    replay_jsons = replay_manager.list_jsons(distinct=True)
    matches = {m.match_id: m for m in replay_manager.list_matches(2.0)}
    for j in replay_jsons:
        if matches.get(j.match_id) is None:
            parsed = replay_files.parse_replay(j.replay_file_url, replay_manager)
            db_match = replay_to_db_match(parsed, json_s3_uri=j.json_s3_uri)
            replay_manager.register_match(db_match)


def get_all_matches2(replay_manager: ReplayManager) -> list[MatchInfo]:
    """Faster but doesn't register missing. use once we always save matches to db."""
    with log_time("listing"):
        listing = replay_manager.list_matches(2.0)
    with log_time("convert"):
        converted = [match_to_matchinfo(m) for m in listing]
    return converted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    constring = os.getenv("DATABASE_URL")
    print("!!", constring)
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(
            session,
            auto_commit=True,
            notify=False,
        )
        with log_time("listing jsons"):
            json_count = len(replay_manager.list_jsons(distinct=True))
        print(json_count)
        with log_time("get all matches"):
            for _ in get_all_matches(replay_manager):
                pass
        with log_time("get all matches2"):
            get_all_matches2(replay_manager)
