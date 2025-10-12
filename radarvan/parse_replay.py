"""Parse replay file."""

import argparse
import sys
import pathlib
import json
import httpx
from cncstats_types import EnhancedReplay
PARSE_URL = "https://cncstats.herokuapp.com/replay"


def parse_replay_data(data: bytes):
    response = httpx.post(PARSE_URL, files={"file": data})
    print(response)
    # print(response.json())
    pathlib.Path("./test.json").write_text(json.dumps(response.json()))
    validated = EnhancedReplay.model_validate(response.json())
    print(validated.Header)
    print(validated.Summary)
    return validated

if __name__ == "__main__":
    filename = sys.argv[1]
    path = pathlib.Path(filename)
    data = path.read_bytes()
    parse_replay_data(data)
