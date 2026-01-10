"""Get match info from a replay."""

from typing import DefaultDict
from collections import defaultdict
from collections.abc import Iterator
from log_time import log_time
import json
import logging
import os
from datetime import datetime, UTC
from pathlib import Path

import db
import replay_files
import utils
from api_types import General, MatchInfo, Player, Team
from cncstats_types import EnhancedReplay
from db_utils import DatabaseManager, ReplayManager

logger = logging.getLogger(__name__)


def winner_override(match_id: int) -> Team | None:
    if match_id == 545219640:
        return Team.TWO
    return None


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
    elif winner == Team.NONE or winner == Team.OBSERVER:
        notes = "No team won?"
        incomplete = "No team won?"
    # if winner == Team.OBSERVER:
    #     notes = ""
    if override := winner_override(replay.replay_id()):
        winner = override

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
    duration_minutes = utils.duration_minutes(replay)
    if _winners:
        winner = _winners[0].Team
        incomplete = ""
        logger.info(f"\n winner {winner} \n")
        if winner == Team.NONE:
            logger.info(f"No winner found in replay {replay.Summary=}")
    if not _winners:
        winner = Team.NONE
        incomplete = "Likely Mismatch :("
    elif winner == Team.NONE or winner == Team.OBSERVER:
        notes = "No team won?"
        incomplete = "No team won?"
    if duration_minutes < 2:
        incomplete = "Too Short"

    if override := winner_override(replay.replay_id()):
        winner = override

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
    winner = db_match.winning_team_id
    if override := winner_override(db_match.match_id):
        winner = override

    return MatchInfo(
        id=db_match.match_id,
        timestamp=db_match.timestamp,
        map=db_match.map,
        winning_team=winner,
        players=players,
        duration_minutes=db_match.duration_minutes,
        filename=db_match.filename,
        incomplete=db_match.incomplete or "",
        notes=db_match.notes,
    )


def get_all_matches(replay_manager: ReplayManager) -> Iterator[MatchInfo]:
    replay_jsons = replay_manager.list_jsons()
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
    replay_jsons = replay_manager.list_jsons()
    matches = {m.match_id: m for m in replay_manager.list_matches(0.0)}
    for j in replay_jsons:
        if matches.get(j.match_id) is None:
            parsed = replay_files.parse_replay(j.replay_file_url, replay_manager)
            db_match = replay_to_db_match(parsed, json_s3_uri=j.json_s3_uri)
            try:
                replay_manager.register_match(db_match)
                matches[db_match.match_id] = db_match
            except Exception as e:
                logger.warning(f"Can not add match {repr(e)}")
                continue


def reparse_replay(match_id: int, replay_manager: ReplayManager) -> MatchInfo | None:
    reparsed = replay_files.reparse(match_id, replay_manager, force=True)
    if reparsed is None:
        logger.info("No reparse needed")
        return None
    parsed_replay, json_s3 = reparsed
    update_match = replay_to_db_match(parsed_replay, json_s3)
    update_match.created_at = datetime.now(UTC)
    replay_manager.update_match(update_match)
    return match_from_replay(parsed_replay)
    return parsed_replay


def filter_match(db_match: db.Match) -> bool:
    # remove comp stomps
    teams: DefaultDict[int, list[str]] = defaultdict(list)
    if len(db_match.players) == 2:
        return True
    for p in db_match.players:
        teams[p.team_id].append(p.player_name)
    for team in teams.values():
        if set(team) == {"CPU"}:
            logger.info(f"Filtering compstom {teams}")
            return False
    # remove ffa
    if len(set(teams.keys())) == 1:
        logger.info(f"Filtering ffa {teams}")
        return False
    return True


def get_all_matches2(replay_manager: ReplayManager) -> list[MatchInfo]:
    """Faster but doesn't register missing. use once we always save matches to db."""
    with log_time("listing"):
        listing = replay_manager.list_matches(2.0)
    filtered = [l for l in listing if filter_match(l)]

    with log_time("convert"):
        converted = [match_to_matchinfo(m) for m in filtered]
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
            jsons = replay_manager.list_jsons()
        # print(json_count)
        # with log_time("get all matches"):
        #     for _ in get_all_matches(replay_manager):
        #         pass
        # with log_time("get all matches2"):
        #     get_all_matches2(replay_manager)
        for j in jsons:
            reparse_replay(j.match_id, replay_manager)
