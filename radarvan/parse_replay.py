"""Parse replay file."""

from .db_utils import DatabaseManager

import os

import sys
import pathlib
import json
import httpx
from .cncstats_types import EnhancedReplay, Player
from .db_utils import ReplayManager
import logging
from .game_composition import categorize_game_type

logger = logging.getLogger(__name__)

# PARSE_URL = "https://cncstats.herokuapp.com/replay"
PARSE_URL = "http://cncstats.computersrfun.org:8080/replay"


def reassign_1v1_teams(players: list[Player]) -> list[Player]:
    """Reasign teams for 1v1s as players may be team less."""
    new_players: list[Player] = []
    for i, p in enumerate(players, 1):
        if p.Faction > -2:
            copy = p.model_copy(update={"Team": i}, deep=True)
        else:
            copy = p.model_copy()
        new_players.append(copy)
    return new_players


def parse_replay_data(
    data: bytes, replay_manager: ReplayManager, debug=False
) -> EnhancedReplay:
    logger.info("Calling cncstats to parse replay")
    response = httpx.post(PARSE_URL, files={"file": data}, timeout=30)
    if debug:
        print(response.json())
        pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    logger.info(
        f"ccnstats responded with replay in {response.elapsed.total_seconds()}s "
    )
    validated = EnhancedReplay.model_validate(response.json())
    players = [p for p in validated.Header.Metadata.Players if p.Faction > -2]
    composition = categorize_game_type(players)
    if composition.is_1v1:
        validated.Header.Metadata.Players = reassign_1v1_teams(
            validated.Header.Metadata.Players
        )
        logger.info(f"Reassigned teams for 1v1 {validated.Header.Metadata.Players}")

    overrides = replay_manager.get_overrides()
    override = overrides.get(validated.replay_id(), None)
    if override is not None:
        for ps in validated.Summary:
            override_value = ps.Team == override.winning_team_id
            logger.warning(
                f"Overriding {validated.replay_id()} {ps.Team} to {override.winning_team_id} {override_value=}"
            )
            ps.Win = override_value

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
