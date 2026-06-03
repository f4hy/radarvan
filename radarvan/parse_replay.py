"""Parse replay file."""

from .db_utils import DatabaseManager

import os

import sys
import pathlib
import json
import httpx
from .cncstats_model.zhreplay import EnhancedReplayV2
from .cncstats_model.header import Player
from .db_utils import ReplayManager
import structlog
from .game_composition import categorize_game_type, PlayerAdapter
from functools import cache

logger = structlog.get_logger(__name__)


# PARSE_URL = "https://cncstats.herokuapp.com/replay"
PARSE_URL = "http://cncstats.computersrfun.org:8080/replay"


@cache
def http_client() -> httpx.Client:
    token = os.environ["CNCSTATS_APIKEY"]
    headers = {"Authorization": f"Bearer {token}"}
    logger.info("Building httpx client", token_len=len(token))
    return httpx.Client(timeout=30, headers=headers)


def reassign_1v1_teams(players: list[Player]) -> list[Player]:
    """Reasign teams for 1v1s as players may be team less."""
    new_players: list[Player] = []
    for i, p in enumerate(players, 1):
        if p.type in ("H", "C"):
            copy = p.model_copy(update={"team": str(i)}, deep=True)
        else:
            copy = p.model_copy()
        new_players.append(copy)
    return new_players


def parse_replay_data(
    data: bytes, replay_manager: ReplayManager, debug: bool = False
) -> EnhancedReplayV2:
    logger.info("Calling cncstats to parse replay")
    response = http_client().post(PARSE_URL, files={"file": data})
    if debug:
        print(response.json())
        pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    logger.info("cncstats responded", elapsed_s=response.elapsed.total_seconds(), resp_headers=response.headers)
    validated = EnhancedReplayV2.model_validate(response.json())
    header_metadata = validated.header.metadata if validated.header else None
    header_players_raw = (header_metadata.players if header_metadata else None) or []
    players = [
        PlayerAdapter(team=int(p.team or "-1"), type=p.type)
        for p in header_players_raw
        if p.type in ("H", "C")
    ]
    composition = categorize_game_type(players)
    if composition.is_1v1 and header_metadata is not None:
        header_metadata.players = reassign_1v1_teams(header_metadata.players or [])
        logger.info("reassigned teams for 1v1", players=header_metadata.players)

    overrides = replay_manager.get_overrides()
    override = overrides.get(validated.replay_id, None)
    if override is not None:
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
