"""Manual paths for now."""

from typing import Generator, Iterator
import httpx
import logging
import fsspec
from cncstats_types import EnhancedReplay
from functools import cache
from parse_replay import parse_replay_data
import os
import utils
from log_time import log_time
from cachetools import cached, LRUCache
import db_utils
from db_utils import ReplayManager
from datetime import datetime

logger = logging.getLogger(__name__)
modus = "Modus_09BAC013F91C"
bill = "131_5211058E5C33"

s3_root = "s3://generals-stats/radarvan/dev/"


@cache
def get_fs() -> fsspec.AbstractFileSystem():
    return fsspec.filesystem("s3")


def test_connection():
    fs = get_fs()
    fs.write_text(f"{s3_root}test.txt", "test")
    listing = fs.ls(s3_root)
    logger.info(f"Listing {listing=}")


def save_replay_if_missing(
    replay_path: str, save_path: str, replay_manager: ReplayManager
) -> None:
    if replay_manager.get_replay_file(replay_path):
        return
    fs = get_fs()
    with log_time(f"Does not exist, saving {replay_path}", logger):
        raw_data = fsspec.filesystem("http").read_bytes(replay_path)
        fs.write_bytes(save_path, raw_data)
    replay_manager.register_replay(replay_path, save_path)


# @cached(cache=LRUCache(maxsize=12))
def parse_replay(path: str, replay_manager: ReplayManager) -> EnhancedReplay:
    replay_path = path.replace("https://www.gentool.net/data/zh/", s3_root)
    save_replay_if_missing(path, replay_path, replay_manager)

    json_path = replay_path.replace(".rep", ".json")
    logger.info(f"{json_path=} {replay_path=}")

    fs = get_fs()
    existing = replay_manager.get_parsed_file(json_path)
    if existing:
        with log_time(f"reading {json_path}", logger):
            json_data = fs.read_text(json_path)
        with log_time(f"Validing {json_path}", logger):
            parsed_replay = EnhancedReplay.model_validate_json(json_data)
    else:
        logger.info(f"Does not exist {json_path=}")
        raw_replay = fs.read_bytes(replay_path)
        parsed_replay = parse_replay_data(raw_replay)
        fs.write_text(json_path, parsed_replay.model_dump_json())
        replay_manager.save_parsed_json(
            replay_id=parsed_replay.replay_id(),
            original_replay_file_url=path,
            json_s3_uri=json_path,
            game_timestamp=datetime.fromtimestamp(parsed_replay.Header.TimeStampBegin),
        )

    logger.info(f"Finished parsing replay {path=}")
    parsed_replay.Header.FileName = path
    return parsed_replay


def path_filter(url: str) -> bool:
    types = {f"_{i}v{i}_" for i in range(5)}
    return any(t in url for t in types)


def get_all_replays(replay_manager: ReplayManager) -> Iterator[EnhancedReplay]:
    uris = {
        j.json_s3_uri: j.replay_file_url
        for j in replay_manager.list_jsons()
        if path_filter(j.replay_file_url)
    }
    fs = get_fs()
    chunk_size = 50
    for i in range(0, len(uris), chunk_size):
        data_chunk = fs.cat(list(uris.keys())[i : i + chunk_size])
        for p, d in data_chunk.items():
            parsed = EnhancedReplay.model_validate_json(d)
            parsed.Header.FileName = uris[fs.unstrip_protocol(p)]
            if utils.duration_minutes(parsed) > 2.0:
                logger.info(f"Yielding {parsed.Header.FileName}")
                yield parsed
