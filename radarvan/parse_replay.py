"""Parse replay file."""

from db_utils import DatabaseManager

import os
from api_types import Team

import sys
import pathlib
import json
import httpx
from cncstats_types import EnhancedReplay
from db_utils import ReplayManager
import logging

logger = logging.getLogger(__name__)

# PARSE_URL = "https://cncstats.herokuapp.com/replay"
PARSE_URL = "http://cncstats.computersrfun.org:8080/replay"


def winner_override(match_id: int) -> Team | None:
    if match_id == 545219640:
        return Team.TWO
    if match_id == 623834125:
        return Team.THREE
    if match_id == 352169906:
        return Team.THREE
    if match_id == 350832203:
        return Team.NONE
    return None


def parse_replay_data(data: bytes, replay_manager: ReplayManager, debug=False):
    logger.info("Calling cncstats to parse replay")
    response = httpx.post(PARSE_URL, files={"file": data}, timeout=30)
    if debug:
        print(response.json())
        pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    logger.info(
        f"ccnstats responded with replay in {response.elapsed.total_seconds()}s "
    )
    validated = EnhancedReplay.model_validate(response.json())

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
    conn_str = os.getenv("DATABASE_URL")
    db_manager = DatabaseManager(conn_str)

    path = pathlib.Path(filename)
    data = path.read_bytes()
    with db_manager.get_session() as session:
        replay_manager = ReplayManager(session)

        validated = parse_replay_data(data, replay_manager, debug=True)
