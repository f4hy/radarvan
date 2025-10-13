"""Manual paths for now."""

import httpx
import logging
import fsspec
from cncstats_types import EnhancedReplay
from functools import cache
from parse_replay import parse_replay_data

logger = logging.getLogger(__name__)
modus = "Modus_09BAC013F91C"
bill = "131_5211058E5C33"

s3_root = "s3://generals-stats/radarvan/dev/"


REPLAYS = [
    "https://www.gentool.net/data/zh/2025_09_September/25_Thursday/Modus_09BAC013F91C/03-40-07_3v3_Skip_OneThree_WildCard_Neo_Modus_Syn.rep",
    "https://www.gentool.net/data/zh/2025_09_September/25_Thursday/Modus_09BAC013F91C/02-50-23_4v4_Skip_WildCard_OneThree_HardAI_Modus_Syn_Pancake_Neo.rep",
    "https://www.gentool.net/data/zh/2025_09_September/25_Thursday/Modus_09BAC013F91C/02-07-26_4v4_Skip_OneThree_WildCard_HardAI_Syn_Modus_Neo_Pancake.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/01-42-30_2v2_Skip_WLD_Mod_Pancake.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/01-50-50_2v2_Skip_WLD_Mod_Pancake.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/02-09-26_2v2_Skip_WLD_Pancake_Mod.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/02-34-50_2v2_Skip_WLD_Pancake_Mod.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/02-46-00_2v2_Skip_WLD_Pancake_Mod.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/03-12-52_2v2_WLD_Skip_Mod_Pancake.rep",
    "https://www.gentool.net/data/zh/2025_10_October/09_Thursday/Mod_09BAC013F91C/03-14-48_2v2_WLD_Skip_Mod_Pancake.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/01-31-27_2v2_Mod_Pancake_Neo_131.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/01-40-54_2v2_Mod_Pancake_131_Neo.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/01-51-56_2v2_Mod_Pancake_Neo_131.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/02-10-57_2v2_Mod_Pancake_131_Neo.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/02-47-34_2v2_Mod_Pancake_131_Neo.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/02-49-16_2v2_Mod_Pancake_131_Neo.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/02-34-51_2v2_Mod_Pancake_Neo_131.rep",
    "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/03-10-42_1v1v1v1v1v1_Neo_131_Pancake_Mod_HardAI_HardAI.rep",
]

# REPLAYS = [
#     # "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/02-49-16_2v2_Mod_Pancake_131_Neo.rep",
#     "https://www.gentool.net/data/zh/2025_10_October/11_Saturday/131_5211058E5C33/02-34-51_2v2_Mod_Pancake_Neo_131.rep"
# ]

@cache
def get_fs() -> fsspec.AbstractFileSystem():
    return fsspec.filesystem("s3")


def test_connection():
    fs = get_fs()
    fs.write_text(f"{s3_root}test.txt", "test")
    listing = fs.ls(s3_root)
    logger.info(f"Listing {listing=}")


@cache
def parse_replay(path: str) -> EnhancedReplay:
    replay_path = path.replace("https://www.gentool.net/data/zh/", s3_root)
    json_path = replay_path.replace(".rep", ".json")
    logger.info(f"{json_path=} {replay_path=}")
    fs = get_fs()
    if not fs.exists(replay_path):
        logger.info(f"Does not exist {replay_path=}")
        raw_data = fsspec.filesystem("http").read_bytes(path)
        fs.write_bytes(replay_path, raw_data)
    if fs.exists(json_path):
        logger.info(f"reading {json_path=}")
        json_data = fs.read_text(json_path)
        logger.info(f"validating {json_path=}")
        parsed_replay = EnhancedReplay.model_validate_json(json_data)
    else:
        logger.info(f"Does not exist {json_path=}")
        raw_replay = fs.read_bytes(replay_path)
        parsed_replay = parse_replay_data(raw_replay)
        fs.write_text(json_path, parsed_replay.model_dump_json())
    logger.info("Finished parsing replay")
    return parsed_replay


def get_parsed_replays(replay_paths: list[str]) -> list[EnhancedReplay]:
    logger.info(f"getting {replay_paths=}")
    return [parse_replay(path) for path in replay_paths]
