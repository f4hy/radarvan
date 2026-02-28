"""Manual paths for now."""

from db_utils import ReplayManager

from collections.abc import Generator
import logging
import fsspec
from cncstats_types import EnhancedReplay
from functools import cache
from db_utils import DatabaseManager

import os
import utils
import replay_files

logger = logging.getLogger(__name__)
modus = "Modus_09BAC013F91C"
bill = "131_5211058E5C33"

s3_root = "s3://generals-stats/radarvan/dev/"

REPLAYS: list[str] = []

if os.getenv("DEV"):
    REPLAYS = REPLAYS[:10]


@cache
def get_fs() -> fsspec.AbstractFileSystem():
    return fsspec.filesystem("s3")


def test_connection() -> None:
    fs = get_fs()
    fs.write_text(f"{s3_root}test.txt", "test")
    listing = fs.ls(s3_root)
    logger.info(f"Listing {listing=}")


def get_parsed_replays(
    replay_paths: list[str],
    replay_manager: ReplayManager,
) -> Generator[EnhancedReplay]:
    logger.info(f"getting {len(replay_paths)=}")
    for path in replay_paths:
        if "1v1v1v1" in path or "2v4" in path:
            continue
        parsed = replay_files.parse_replay(path, replay_manager)
        if utils.duration_minutes(parsed) > 2.0:
            logger.info(f"Yielding {parsed.Header.FileName}")
            yield parsed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conn_str = os.getenv("DATABASE_URL")
    db_manager = DatabaseManager(conn_str)
    with db_manager.get_session() as session:
        replay_manager = ReplayManager(session)
        for path in REPLAYS:
            print(path)
            if "1v1v1v1" in path or "2v4" in path:
                continue
            parsed = replay_files.parse_replay(path, replay_manager)
