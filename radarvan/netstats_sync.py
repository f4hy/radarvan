"""Fetch client logs for recent matches, keep a raw copy in S3 and the summary in Postgres."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import structlog

from . import replay_files, s3_store
from .api_types import NetstatsSummary
from .cncstats_client import CncstatsClient
from .db import NetstatsStatus
from .netstats import PARSER_VERSION, parse_match_netstats, summarize
from .repositories import NetstatsRepo
from .repositories.netstats import NetstatsWork

logger = structlog.get_logger(__name__)

LOOKBACK = timedelta(days=3)
MAX_ATTEMPTS = 8
MAX_PER_RUN = 60


class Parsed(NamedTuple):
    status: NetstatsStatus
    summary: NetstatsSummary | None


def netstats_s3_uri(match_id: int) -> str:
    return f"{replay_files.s3_root}netstats/{match_id}.zip"


def read_archived(store: s3_store.S3Store, match_id: int) -> bytes | None:
    try:
        return store.read_bytes(netstats_s3_uri(match_id))
    except FileNotFoundError:
        return None


def latest_logs_zip(
    client: CncstatsClient, store: s3_store.S3Store, match_id: int
) -> bytes | None:
    """cncstats (more players' logs may have arrived since), else our archived copy."""
    return client.get_logs_zip(match_id) or read_archived(store, match_id)


def _fetch_and_archive(
    client: CncstatsClient, store: s3_store.S3Store, match_id: int
) -> bytes | None:
    zip_bytes = client.get_logs_zip(match_id)
    if zip_bytes is None:
        return read_archived(store, match_id)
    store.write_bytes(netstats_s3_uri(match_id), zip_bytes)
    return zip_bytes


def _parse(zip_bytes: bytes | None, match_id: int) -> Parsed:
    if zip_bytes is None:
        return Parsed(NetstatsStatus.NO_LOGS, None)
    try:
        summary = summarize(parse_match_netstats(zip_bytes, match_id))
    except Exception:
        logger.exception("netstats parse failed", match_id=match_id)
        return Parsed(NetstatsStatus.PARSE_ERROR, None)
    if not summary.roster:
        return Parsed(NetstatsStatus.NO_LOGS, None)
    return Parsed(NetstatsStatus.OK, summary)


def _process(
    repo: NetstatsRepo,
    work: NetstatsWork,
    load: Callable[[int], bytes | None],
    fresh: bool,
) -> NetstatsStatus | None:
    try:
        zip_bytes = load(work.match_id)
    except Exception:
        logger.exception("netstats fetch failed", match_id=work.match_id)
        repo.session.rollback()
        return None
    # A re-derive with nothing archived keeps what the old parser stored.
    if zip_bytes is None and not fresh:
        return None
    parsed = _parse(zip_bytes, work.match_id)
    attempts = work.attempts + fresh
    # Every player's logs are in: nothing left to wait for.
    if parsed.summary and all(r.has_logs for r in parsed.summary.roster):
        attempts = max(attempts, MAX_ATTEMPTS)
    repo.save(work.match_id, parsed.status, PARSER_VERSION, parsed.summary, attempts)
    return parsed.status


def sync_netstats(
    repo: NetstatsRepo,
    client: CncstatsClient,
    store: s3_store.S3Store,
    now: datetime | None = None,
) -> Counter[str]:
    result = Counter[str]()
    since = (now or datetime.now(UTC)) - LOOKBACK
    # One match at a time: a parse holds a whole log zip in memory.
    for work in repo.matches_to_fetch(since, MAX_ATTEMPTS, MAX_PER_RUN):
        status = _process(
            repo, work, lambda m: _fetch_and_archive(client, store, m), fresh=True
        )
        result[status or "fetch_failed"] += 1
    for work in repo.stale_rows(PARSER_VERSION, MAX_PER_RUN):
        if _process(repo, work, lambda m: read_archived(store, m), fresh=False):
            result["rederived"] += 1
    logger.info("netstats sync done", **result)
    return result
