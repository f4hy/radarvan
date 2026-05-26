"""Manual paths for now."""

import hashlib
import re
import structlog
import fsspec
from datetime import date
from typing import NamedTuple
from .cncstats_model.zhreplay import EnhancedReplayV2
from functools import cache
from .parse_replay import parse_replay_data
from . import utils
from .log_time import log_time
from .db_utils import ReplayManager
import boto3
from urllib.parse import urlparse
from botocore.config import Config

logger = structlog.get_logger(__name__)


class ParsedReplayResult(NamedTuple):
    replay: EnhancedReplayV2
    json_path: str


modus = "Modus_09BAC013F91C"
bill = "131_5211058E5C33"

s3_root = "s3://generals-stats/radarvan/dev/"


@cache
def get_fs() -> fsspec.AbstractFileSystem:
    return fsspec.filesystem("s3")


def presigned_url(s3_path: str) -> str:
    """preSign a s3_path"""
    parsed = urlparse(s3_path)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    # Create S3 client
    s3_client = boto3.client(
        "s3", region_name="us-east-2", config=Config(signature_version="s3v4")
    )

    # Generate presigned URL
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )

    return str(url)


def test_connection() -> None:
    fs = get_fs()
    fs.write_text(f"{s3_root}test.txt", "test")
    listing = fs.ls(s3_root)
    logger.info("listing", listing=listing)


def save_replay_if_missing(
    replay_path: str, save_path: str, replay_manager: ReplayManager
) -> None:
    if replay_manager.get_replay_file(replay_path):
        return
    fs = get_fs()
    with log_time("saving replay", logger, path=replay_path):
        raw_data = fsspec.filesystem("http").read_bytes(replay_path)
        fs.write_bytes(save_path, raw_data)
    replay_manager.register_replay(replay_path, save_path, compute_hash(raw_data))


def with_filename(replay: EnhancedReplayV2, path: str) -> EnhancedReplayV2:
    """Return a copy of replay with header.replay_name set to path."""
    return replay.model_copy(
        update={"header": replay.header.model_copy(update={"replay_name": path})}
    )


def parse_json(json_path: str) -> EnhancedReplayV2:
    fs = get_fs()
    with log_time("reading json", logger, path=json_path):
        json_data = fs.read_text(json_path)
    with log_time("validating json", logger, path=json_path):
        parsed_replay = EnhancedReplayV2.model_validate_json(json_data)
    return parsed_replay


# @cached(cache=LRUCache(maxsize=12))
@utils.log_duration
def parse_replay(path: str, replay_manager: ReplayManager) -> EnhancedReplayV2:
    replay_file = replay_manager.get_replay_file(path)
    if replay_file is not None:
        replay_path = replay_file.s3_uri
    else:
        replay_path = path.replace("https://www.gentool.net/data/zh/", s3_root).replace(
            "https://generals-public.s3.us-east-2.amazonaws.com/reps/", s3_root
        )
        save_replay_if_missing(path, replay_path, replay_manager)

    json_path = replay_path.replace(".rep", ".json")
    logger.debug("paths", json_path=json_path, replay_path=replay_path)

    fs = get_fs()
    existing = replay_manager.get_parsed_file(json_path)
    if existing and existing.is_v2 is True:
        with log_time("reading json", logger, path=json_path):
            json_data = fs.read_text(json_path)
        with log_time("validating json", logger, path=json_path):
            parsed_replay = EnhancedReplayV2.model_validate_json(json_data)
    else:
        logger.info("json does not exist", json_path=json_path)
        raw_replay = fs.read_bytes(replay_path)
        parsed_replay = parse_replay_data(raw_replay, replay_manager)
        fs.write_text(json_path, parsed_replay.model_dump_json(by_alias=True))
        replay_manager.save_parsed_json(
            parsed_replay=parsed_replay,
            original_replay_file_url=path,
            json_s3_uri=json_path,
        )

    logger.debug("finished parsing replay", path=path)
    return with_filename(parsed_replay, path)


def reparse(
    match_id: int, replay_manager: ReplayManager, force: bool = False
) -> ParsedReplayResult | None:
    logger.info("reparsing", match_id=match_id)
    existing = replay_manager.get_replay_json_by_match_id(match_id)
    logger.info("existing", existing=existing)

    if existing is None:
        return None

    json_path = existing.json_s3_uri
    original_path = existing.replay_file_url
    replay_path = existing.replay_file.s3_uri

    fs = get_fs()
    existing_replay: EnhancedReplayV2 | None = None
    if existing.is_v2:
        existing_data = fs.read_text(json_path)
        existing_replay = EnhancedReplayV2.model_validate_json(existing_data)
        if utils.duration_minutes(existing_replay) < 2.0:
            logger.warning("Too short, skipping")
            return None

    raw_replay = fs.read_bytes(replay_path)
    parsed_replay = with_filename(
        parse_replay_data(raw_replay, replay_manager), original_path
    )

    if existing_replay == parsed_replay and not force:
        logger.warning("No change in replay, not resaving")
        return None

    return reparse_paths(json_path, original_path, replay_path, replay_manager)


def reparse_paths(
    json_path: str, original_path: str, replay_path: str, replay_manager: ReplayManager
) -> ParsedReplayResult | None:
    logger.info("reparsing", original_path=original_path)

    fs = get_fs()
    raw_replay = fs.read_bytes(replay_path)
    parsed_replay = with_filename(
        parse_replay_data(raw_replay, replay_manager), original_path
    )

    replay_manager.save_parsed_json(
        json_s3_uri=json_path,
        original_replay_file_url=original_path,
        parsed_replay=parsed_replay,
    )
    fs.write_text(json_path, parsed_replay.model_dump_json(by_alias=True))
    return ParsedReplayResult(replay=parsed_replay, json_path=json_path)


def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def upload_and_parse(
    data: bytes,
    file_hash: str,
    replay_manager: ReplayManager,
    mac_id: str | None = None,
    board_id: str | None = None,
    uploader_name: str | None = None,
    client_version: str | None = None,
    source_tag: str | None = None,
) -> ParsedReplayResult:
    """Parse raw replay bytes, then persist .rep + .json to S3 and register in DB.

    Parses before any persistence so a parser failure leaves no orphan rows or S3 objects.
    """
    original_url = f"upload:{file_hash}"
    parsed_replay = with_filename(parse_replay_data(data, replay_manager), original_url)

    s3_uri = f"{s3_root}uploads/{file_hash}.rep"
    json_path = f"{s3_root}uploads/{file_hash}.json"
    fs = get_fs()
    fs.write_bytes(s3_uri, data)
    fs.write_text(json_path, parsed_replay.model_dump_json(by_alias=True))

    replay_manager.register_uploaded_replay(
        original_url=original_url,
        s3_uri=s3_uri,
        file_hash=file_hash,
        source_date=date.today(),
        mac_id=mac_id,
        board_id=board_id,
        uploader_name=uploader_name,
        client_version=client_version,
        source_tag=source_tag,
    )
    replay_manager.save_parsed_json(
        json_s3_uri=json_path,
        original_replay_file_url=original_url,
        parsed_replay=parsed_replay,
    )

    return ParsedReplayResult(replay=parsed_replay, json_path=json_path)


def path_filter(url: str) -> bool:
    multi_computer = re.search("HardAI.*HardAI", url)
    if multi_computer:
        return False
    types = {f"_{i}v{i}_" for i in range(5)}
    return any(t in url for t in types)


def map_basename(map_path: str) -> str:
    return map_path.split("/")[-1] if map_path else "Unknown"
