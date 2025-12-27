"""Parse replay file."""

from api_types import General, MatchInfo, Player, Team

import sys
import pathlib
import json
import httpx
from cncstats_types import EnhancedReplay
import logging

logger = logging.getLogger(__name__)

PARSE_URL = "https://cncstats.herokuapp.com/replay"


def winner_override(match_id: int) -> Team | None:
    if match_id == 545219640:
        return Team.TWO
    return None


def parse_replay_data(data: bytes, debug=False):
    logger.info("Calling cncstats to parse replay")
    response = httpx.post(PARSE_URL, files={"file": data})
    if debug:
        print(response.json())
        pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    logger.info(f"Pared replay in {response.elapsed.total_seconds()}s ")
    validated = EnhancedReplay.model_validate(response.json())
    if override := winner_override(validated.replay_id()):
        for ps in validated.Summary:
            logger.warning(
                f"Overriding {validated.replay_id()} {ps.Team} to {override}"
            )
            override_value = ps.Team == override
            ps.Win = override_value

    return validated


if __name__ == "__main__":
    filename = sys.argv[1]
    path = pathlib.Path(filename)
    data = path.read_bytes()
    validated = parse_replay_data(data, debug=True)
