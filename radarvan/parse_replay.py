"""Parse replay file."""

import argparse
import sys
import pathlib
import json
import httpx
from cncstats_types import EnhancedReplay
import logging
logger = logging.getLogger(__name__)

PARSE_URL = "https://cncstats.herokuapp.com/replay"


def parse_replay_data(data: bytes, debug=False):
    logger.info("Calling cncstats to parse replay")
    response = httpx.post(PARSE_URL, files={"file": data})
    if debug:
        print(response.json())
        pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    validated = EnhancedReplay.model_validate(response.json())
    return validated

if __name__ == "__main__":
    filename = sys.argv[1]
    path = pathlib.Path(filename)
    data = path.read_bytes()
    validated = parse_replay_data(data, debug=True)
