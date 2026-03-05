"""Get match info from a replay."""

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
from .game_composition import GameComposition, categorize_game_type
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WinnerAndNotes:
    wining_team: int
    notes: str = ""


def determine_winner(replay: EnhancedReplay, players: list[Player]) -> WinnerAndNotes:
    _winners = [p for p in replay.Summary if p.Win is True]
    if not _winners:
        return WinnerAndNotes(
            wining_team=Team.NONE,
        )
    player_map = {p.name: p for p in players}
    winner_player = player_map.get(_winners[0].Name)
    if winner_player is None:
        logger.info(
            f"Winner name {_winners[0].Name!r} not in player list {list(player_map)}"
        )
        return WinnerAndNotes(wining_team=Team.NONE, notes="Winner not in player list")
    winning_team = winner_player.team
    if winning_team == Team.NONE or winning_team == Team.OBSERVER:
        logger.info(f"No winner found in replay {replay.Summary=}")
        return WinnerAndNotes(wining_team=Team.NONE, notes="No team won?")
    return WinnerAndNotes(
        wining_team=winning_team,
    )


def is_incomplete(replay: EnhancedReplay) -> str | None:
    head = replay.Header
    if (
        sum(head.Desync or [])
        + sum(head.UnusedDesync or [])
        + sum(head.MoreUnusedDesync or [])
    ) > 0:
        return "Replay header Mismatch"
    if (sum(head.QuitEarly or [])) > 0:
        return "Quit Early"
    if (sum(head.Disconnect or [])) > 0:
        return "Disconnect"

    duration_minutes = utils.duration_minutes(replay)
    if duration_minutes < 2:
        return "Too Short"
    _winners = [p for p in replay.Summary if p.Win is True]
    if not _winners:
        real_players = [p for p in replay.Header.Metadata.Players if p.Faction > -2]
        composition = categorize_game_type(real_players)
        if composition.is_ffa:
            return None
        return "No team won"
    return ""


def match_from_replay(replay: EnhancedReplay) -> MatchInfo | None:
    duration_minutes = utils.duration_minutes(replay)
    if duration_minutes < 2:
        logger.info("under 2 minutes, not a real game")
        return None
    players = utils.players_from_replay(replay)
    winner_data = determine_winner(replay, players)
    incomplete = is_incomplete(replay=replay)

    return MatchInfo(
        id=replay.replay_id(),
        timestamp=replay.Header.TimeStampBegin,
        date=datetime.fromtimestamp(replay.Header.TimeStampBegin).date(),
        map=replay.Header.Metadata.MapFile,
        winning_team=winner_data.wining_team,
        players=players,
        duration_minutes=duration_minutes,
        filename=replay.Header.FileName,
        incomplete=incomplete or "",
        notes=incomplete or "",
    )


@utils.log_duration
def replay_to_db_match(replay: EnhancedReplay, json_s3_uri: str) -> db.Match:
    """replay to match."""
    match_id = replay.replay_id()
    players = utils.players_from_replay(replay)
    winner_data = determine_winner(replay, players)
    incomplete = is_incomplete(replay=replay)

    db_players = [
        db.MatchPlayer(
            match_id=match_id,
            player_name=p.name,
            general_id=p.general,
            team_id=p.team,
            color=p.color,
            is_winner=p.won,
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
        incomplete=incomplete or None,
        notes=incomplete,
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
            won=p.is_winner,
        )
        for p in db_players
    ]
    winner = db_match.winning_team_id
    c = db_match.composition
    comp = GameComposition.model_validate(c, from_attributes=True) if c else None
    if db_match.replay_json is None:
        raise ValueError(f"Match {db_match.match_id} has no associated replay JSON")
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
        notes=db_match.notes or "",
        game_version=db_match.game_version,
        composition=comp,
    )


def register_matches(replay_manager: ReplayManager) -> None:
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
    replay_manager.update_match(update_match)
    return match_from_replay(parsed_replay)


def matches_differ(existing: db.Match, new: db.Match) -> bool:
    """Return True if any key fields differ between existing and new match."""
    if existing.map != new.map:
        return True
    if existing.winning_team_id != new.winning_team_id:
        return True
    if round(existing.duration_minutes, 2) != round(new.duration_minutes, 2):
        return True
    if existing.incomplete != new.incomplete:
        return True
    if existing.game_version != new.game_version:
        return True
    existing_players = sorted(
        (p.player_name, p.general_id, p.team_id, p.color, p.is_winner)
        for p in existing.players
    )
    new_players = sorted(
        (p.player_name, p.general_id, p.team_id, p.color, p.is_winner)
        for p in new.players
    )
    return existing_players != new_players


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
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
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


def filter_by_format(
    games: list[MatchInfo], game_format: str | None
) -> list[MatchInfo]:
    """Filter a list of MatchInfo by composition category. Returns unchanged list if format is None."""
    if game_format is None:
        return games
    return [
        g
        for g in games
        if g.composition is not None and g.composition.category == game_format
    ]
