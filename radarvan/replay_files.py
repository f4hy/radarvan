"""Manual paths for now."""

import hashlib
import re
import structlog
import fsspec
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, NamedTuple
from .api_types import MatchInfo
from .cncstats_model.zhreplay import EnhancedReplayV2
from functools import cache
from .parse_replay import parse_replay_data
from . import utils
from .log_time import log_time
from .db_utils import ReplayManager
from .player_ids import resolve_player_name
from .repositories.maps import normalize_map_name
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


@cache
def _s3_client() -> Any:
    # Client construction (credential/endpoint resolution) is expensive and the
    # client is thread-safe; build it once. Callers like routes/files.py sign
    # multiple URLs per request. Typed Any because the precise S3Client type
    # lives in boto3-stubs (dev-only) and TYPE_CHECKING imports are banned here.
    return boto3.client(
        "s3", region_name="us-east-2", config=Config(signature_version="s3v4")
    )


def presigned_url(
    s3_path: str, expires_in: int = 3600, save_as: str | None = None
) -> str:
    """preSign a s3_path. expires_in is the URL validity in seconds (S3 caps at 7 days).

    ``save_as`` names the file the browser should write. It has to be signed
    into the URL rather than set by the caller: the presigned URL points at S3,
    so a cross-origin `<a download>` attribute is ignored and the download
    would land under the S3 key - a content hash. Pass a name from
    `download_filename`.
    """
    parsed = urlparse(s3_path)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    params = {"Bucket": bucket, "Key": key}
    if save_as is not None:
        params["ResponseContentDisposition"] = f'attachment; filename="{save_as}"'

    url = _s3_client().generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires_in,
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
    file_hash = compute_hash(raw_data)
    # `replay_files.file_hash` is uniquely constrained, but the same bytes do
    # legitimately show up under more than one original_url: a replay uploaded
    # via /api/upload_replay is later found on gentool, or gentool serves a
    # byte-identical copy from a second player's directory. Registering the
    # second URL with the same hash raises IntegrityError, which poisons the
    # session and kills the rest of the scrape run - so leave the hash NULL on
    # the duplicate (NULLs don't collide) and let the first row keep it.
    duplicate = replay_manager.get_replay_by_hash(file_hash)
    if duplicate is not None:
        logger.info(
            "replay bytes already registered under another url",
            url=replay_path,
            existing_url=duplicate.original_url,
            file_hash=file_hash,
        )
        replay_manager.register_replay(replay_path, save_path, None)
        return
    replay_manager.register_replay(replay_path, save_path, file_hash)


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
        return EnhancedReplayV2.model_validate_json(json_data)


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
        if not utils.is_long_enough(existing_replay):
            logger.warning("Too short, skipping")
            return None

    raw_replay = fs.read_bytes(replay_path)
    parsed_replay = with_filename(
        parse_replay_data(raw_replay, replay_manager), original_path
    )

    if existing_replay == parsed_replay and not force:
        logger.warning("No change in replay, not resaving")
        return None

    # Pass the replay we just parsed so reparse_paths doesn't re-download and
    # re-parse it (a second S3 read + cncstats call per reparse).
    return reparse_paths(
        json_path, original_path, replay_path, replay_manager, parsed_replay
    )


def reparse_paths(
    json_path: str,
    original_path: str,
    replay_path: str,
    replay_manager: ReplayManager,
    parsed_replay: EnhancedReplayV2 | None = None,
) -> ParsedReplayResult | None:
    """Re-parse a replay from S3 and persist the JSON + DB row.

    ``parsed_replay`` lets a caller that already ran the parser (e.g. ``reparse``,
    which parses to diff against the stored JSON) skip a second download and
    cncstats call; when None, the raw replay is fetched and parsed here.
    """
    logger.info("reparsing", original_path=original_path)

    fs = get_fs()
    if parsed_replay is None:
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


def is_dev_build(zulu_build: str | None) -> bool:
    """A replay is a "dev" replay when its X-Zulu-Build header starts with "dev-"."""
    return bool(zulu_build and zulu_build.startswith("dev-"))


def upload_and_parse(
    data: bytes,
    file_hash: str,
    replay_manager: ReplayManager,
    mac_id: str | None = None,
    board_id: str | None = None,
    uploader_name: str | None = None,
    client_version: str | None = None,
    source_tag: str | None = None,
    zulu_build: str | None = None,
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
        source_date=datetime.now(UTC).date(),
        mac_id=mac_id,
        board_id=board_id,
        uploader_name=uploader_name,
        client_version=client_version,
        source_tag=source_tag,
        zulu_build=zulu_build,
        is_dev=is_dev_build(zulu_build),
    )
    replay_manager.save_parsed_json(
        json_s3_uri=json_path,
        original_replay_file_url=original_url,
        parsed_replay=parsed_replay,
    )

    return ParsedReplayResult(replay=parsed_replay, json_path=json_path)


def map_basename(map_path: str) -> str:
    return map_path.rsplit("/", maxsplit=1)[-1] if map_path else "Unknown"


# Everything outside this set becomes an underscore: in-game names carry
# clan tags, brackets and non-ASCII, and the name is signed into an S3
# `Content-Disposition` header as well as written to a filesystem.
_UNSAFE_IN_FILENAME = re.compile(r"[^A-Za-z0-9_]+")


def _safe_part(text: str) -> str:
    return _UNSAFE_IN_FILENAME.sub("_", text).strip("_") or "unknown"


def download_filename(match: MatchInfo) -> str:
    """The name a match's .rep should be saved as.

    ``2025-08-27-2v2-Alice-Bob-vs-Carl-Dave-Tournament_Desert-84611718.rep``:
    date, format, the sides, the map, and the match id. The stored S3 key is a
    content hash, so without this every downloaded replay lands in the browser
    named after that hash.
    """
    roster = match.roster()
    by_team: dict[int, list[str]] = defaultdict(list)
    # A 1v1 that never went through parse_replay.reassign_1v1_teams has two
    # teamless competitors; each is its own side rather than one joint team.
    solo: list[str] = []
    for slot in roster.competitors:
        name = _safe_part(resolve_player_name(slot.name, slot.color))
        if slot.team > 0:
            by_team[slot.team].append(name)
        else:
            solo.append(name)
    side_names = [sorted(names) for _, names in sorted(by_team.items())]
    side_names.extend([n] for n in sorted(solo))
    sides = ["-".join(names) for names in side_names]
    matchup = "-vs-".join(sides) if sides else "unknown"
    # The composition is what the rest of the app labels the match with; the
    # side sizes are the same answer for a match parsed before it had one.
    game_format = _safe_part(
        match.composition.category
        if match.composition is not None
        else "v".join(str(len(names)) for names in side_names)
    )
    map_name = _safe_part(map_basename(match.map).removesuffix(".map"))
    return f"{match.date.isoformat()}-{game_format}-{matchup}-{map_name}-{match.id}.rep"


def map_key(name: str) -> str:
    """Normalized join key between a Match.map path and a MapData.map_name.

    Match history stores a path (e.g. ``maps/foo/foo.map``); MapData stores a
    canonical name. Strip the path, the ``.map`` suffix, whitespace, and case so
    the two line up.
    """
    return normalize_map_name(map_basename(name).removesuffix(".map"))
