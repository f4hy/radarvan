"""Get match info from a replay."""

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
from tqdm import tqdm

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
            team=db.Team(p.team),
            general=db.General()
        )
        for p in players
    ]
    db_teams = [db.Team() for t in p.team]
    
    return db.Match(
        match_id=match_id,
        json_s3_uri=json_s3_uri,
        timestamp=replay.Header.TimeStampBegin,
        map=replay.Header.Metadata.MapFile,
        winning_team=winner,
        players=db_players,
        duration_minutes=utils.duration_minutes(replay),
        filename=replay.Header.FileName,
        incomplete=incomplete,
        notes=notes,
    )


def match_to_matchinfo(db_match: db.Match) -> MatchInfo:
    """Convert."""
    players = [
        Player(name=p.name, general=p.general, team=p.team, color=p.color)
        for p in db_match.players
    ]
    return MatchInfo(
        id=db_match.match_id,
        timestamp=db_match.timestamp,
        map=db_match.map,
        winning_team=db_match.winning_team,
        players=players,
        duration_minutes=db_match.duration_minutes,
        filename=db_match.json_s3_uri,
        incomplete=db_match.incomplete,
        notes=db_match.notes,
    )


if __name__ == "__main__":
    constring = os.getenv("DATABASE_URL")
    print("!!", constring)
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        jsons = replay_files.all_json_uris(replay_manager)
    i = 1
    for json_uri, replay_file_url in jsons.items():
        print(json_uri, replay_file_url)
        parsed = replay_files.parse_replay(replay_file_url, replay_manager)
        print(parsed)
        db_match = replay_to_db_match(parsed, json_uri)
        print(db_match)

        i += 1
        if i > 1:
            break
