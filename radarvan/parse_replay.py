"""Parse replay file."""

from .db_utils import DatabaseManager

import itertools
import os

import sys
import pathlib
import json
from .cncstats_client import cncstats_client
from .cncstats_model.zhreplay import EnhancedReplayV2
from .cncstats_model.header import Player
from .db_utils import ReplayManager
import structlog
from . import utils
from .game_composition import categorize_game_type, PlayerAdapter

logger = structlog.get_logger(__name__)


def reassign_1v1_teams(players: list[Player]) -> list[Player]:
    """Reasign teams for 1v1s as players may be team less.

    Only the two actual competitors get numbered; observers keep their
    original teamless slot. Numbering every slot instead would spread a
    spectated 1v1 across three or four teams and categorize it as an FFA.
    """
    seats = itertools.count(1)
    return [
        p.model_copy(update={"team": str(next(seats))}, deep=True)
        if utils.is_competitor(p)
        else p.model_copy()
        for p in players
    ]


def parse_replay_data(
    data: bytes, replay_manager: ReplayManager, debug: bool = False
) -> EnhancedReplayV2:
    logger.info("Calling cncstats to parse replay")
    response = cncstats_client().parse_replay(data)
    if debug:
        pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    logger.info(
        "cncstats responded",
        elapsed_s=response.elapsed.total_seconds(),
        resp_headers=response.headers,
    )
    validated = EnhancedReplayV2.model_validate(response.json())
    header_metadata = validated.header.metadata if validated.header else None
    header_players_raw = (header_metadata.players if header_metadata else None) or []
    players = [
        # header team is raw/0-based; categorize_game_type expects the
        # 1-based scheme (0 = no team/FFA) - same conversion as matches.py's
        # winner check. Feeding the raw value in reads a 2v2's "team 0" side
        # as teamless and mistakes the other two for a 1v1.
        PlayerAdapter(team=int(utils.determine_team(p, None)), type=p.type)
        for p in header_players_raw
        if utils.is_competitor(p)
    ]
    composition = categorize_game_type(players)
    if composition.is_1v1 and header_metadata is not None:
        header_metadata.players = reassign_1v1_teams(header_metadata.players or [])
        logger.info("reassigned teams for 1v1", players=header_metadata.players)

    overrides = replay_manager.get_overrides()
    override = overrides.get(validated.replay_id, None)
    if override is not None and override.winning_team_id is not None:
        for ps in validated.summary or []:
            override_value = ps.team == override.winning_team_id
            logger.warning(
                "overriding",
                replay_id=validated.replay_id,
                team=ps.team,
                winning_team_id=override.winning_team_id,
                win=override_value,
            )
            ps.win = override_value

    return validated


if __name__ == "__main__":
    filename = sys.argv[1]
    conn_str = os.getenv("DATABASE_URL", "")
    if not conn_str:
        raise ValueError("DATABASE_URL not set")
    db_manager = DatabaseManager(conn_str)

    path = pathlib.Path(filename)
    data = path.read_bytes()
    with db_manager.get_session() as session:
        replay_manager = ReplayManager(session)

        validated = parse_replay_data(data, replay_manager, debug=True)
