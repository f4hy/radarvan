"""Get match info from a replay."""

from collections import defaultdict
from collections.abc import Iterator
from .log_time import log_time
import logging
import os
from datetime import datetime

from . import db
from . import replay_files
from . import utils
from .api_types import MatchInfo, Player, Team
from .cncstats_types import EnhancedReplay
from .db_utils import DatabaseManager, ReplayManager
from .game_composition import GameComposition
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WinnerAndNotes:
    wining_team: int
    notes: str = ""
    incomplete: str = ""


def determine_winner(replay: EnhancedReplay, players: list[Player]) -> WinnerAndNotes:
    _winners = [p for p in replay.Summary if p.Win is True]
    if not _winners:
        return WinnerAndNotes(
            wining_team=Team.NONE,
            incomplete="Likely Mismatch :(",
        )
    player_map = {p.name: p for p in players}
    winning_team = player_map[_winners[0].Name].team
    if winning_team == Team.NONE or winning_team == Team.OBSERVER:
        logger.info(f"No winner found in replay {replay.Summary=}")
        return WinnerAndNotes(
            wining_team=Team.NONE, notes="No team won?", incomplete="No team won?"
        )
    return WinnerAndNotes(
        wining_team=winning_team,
    )


def match_from_replay(replay: EnhancedReplay) -> MatchInfo | None:
    duration_minutes = utils.duration_minutes(replay)
    if duration_minutes < 2:
        logger.info("under 2 minutes, not a real game")
        return None
    players = utils.players_from_replay(replay)
    winner_data = determine_winner(replay, players)

    return MatchInfo(
        id=replay.replay_id(),
        timestamp=replay.Header.TimeStampBegin,
        date=datetime.fromtimestamp(replay.Header.TimeStampBegin).date(),
        map=replay.Header.Metadata.MapFile,
        winning_team=winner_data.wining_team,
        players=players,
        duration_minutes=duration_minutes,
        filename=replay.Header.FileName,
        incomplete=winner_data.incomplete,
        notes=winner_data.notes,
    )


@utils.log_duration
def replay_to_db_match(replay: EnhancedReplay, json_s3_uri: str) -> db.Match:
    """replay to match."""
    match_id = replay.replay_id()
    players = utils.players_from_replay(replay)
    winner_data = determine_winner(replay, players)

    duration_minutes = utils.duration_minutes(replay)
    if duration_minutes < 2:
        winner_data.incomplete = "Too Short"

    db_players = [
        db.MatchPlayer(
            match_id=match_id,
            player_name=p.name,
            general_id=p.general,
            team_id=p.team,
            color=p.color,
            is_winner=p.team == winner_data.wining_team,
        )
        for p in players
    ]

    return db.Match(
        match_id=match_id,
        json_s3_uri=json_s3_uri,
        timestamp=datetime.fromtimestamp(replay.Header.TimeStampBegin),
        map=replay.Header.Metadata.MapFile,
        winning_team_id=winner_data.wining_team,
        players=db_players,
        duration_minutes=utils.duration_minutes(replay),
        filename=replay.Header.FileName,
        incomplete=winner_data.incomplete,
        notes=winner_data.notes,
        game_version=replay.Header.Version.lower().replace("version", "").strip(),
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
    c = db_match.composition
    comp = GameComposition.model_validate(c, from_attributes=True) if c else None
    return MatchInfo(
        id=db_match.match_id,
        timestamp=db_match.timestamp,
        date=db_match.replay_json.game_date,
        map=db_match.map,
        winning_team=winner,
        players=players,
        duration_minutes=db_match.duration_minutes,
        filename=db_match.filename,
        incomplete=db_match.incomplete or "",
        notes=db_match.notes,
        game_version=db_match.game_version,
        composition=comp,
    )


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
                logger.warning(f"Can not add match {e!r}")
                continue


def reparse_replay(match_id: int, replay_manager: ReplayManager) -> MatchInfo | None:
    reparsed = replay_files.reparse(match_id, replay_manager, force=True)
    if reparsed is None:
        logger.info("No reparse needed")
        return None
    parsed_replay, json_s3 = reparsed
    update_match = replay_to_db_match(parsed_replay, json_s3)
    replay_manager.update_match(
        update_match.match_id,
        json_s3=json_s3,
        winning_team_id=update_match.winning_team_id,
        game_version=update_match.game_version,
        players=update_match.players,
    )
    return match_from_replay(parsed_replay)


def filter_match(db_match: db.Match) -> bool:
    # remove comp stomps
    return True
    # if db_match.composition.is_comp_stomp:
    #     return False
    # if not db_match.composition.is_balanced:
    #     return False
    # if db_match.composition.is_team_game:
    #     return True
    # return False
    # teams: defaultdict[int, list[str]] = defaultdict(list)
    # if len(db_match.players) == 2:
    #     return True
    # for p in db_match.players:
    #     teams[p.team_id].append(p.player_name)
    # for team in teams.values():
    #     if set(team) == {"CPU"}:
    #         # logger.info(f"Filtering compstom {teams}")
    #         return False
    # # remove ffa
    # if len(set(teams.keys())) == 1:
    #     # logger.info(f"Filtering ffa {teams}")
    #     return False
    # return True


def competitive_game_filter(comp: GameComposition | None) -> bool:
    if comp is None:
        return False
    if comp.num_computers > 1:
        return False
    if comp.is_comp_stomp:
        return False
    if not comp.is_balanced:
        return False
    if not comp.is_team_game:
        return False
    return True


def get_match_infos(replay_manager: ReplayManager) -> list[MatchInfo]:
    """Faster but doesn't register missing. use once we always save matches to db."""
    with log_time("listing"):
        listing = replay_manager.list_matches(2.0)
    filtered = [x for x in listing if filter_match(x)]

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
