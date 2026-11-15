"""Fetch client logs for recent matches, keep a raw copy in S3 and the summary in Postgres."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from . import replay_files, s3_store
from .cncstats_client import CncstatsClient
from .netstats import PARSER_VERSION, parse_match_netstats, summarize
from .repositories import NetstatsRepo
from .repositories.netstats import NO_LOGS, OK, PARSE_ERROR

logger = structlog.get_logger(__name__)

LOOKBACK = timedelta(days=3)
MAX_ATTEMPTS = 8
MAX_PER_RUN = 60


@dataclass
class SyncResult:
    fetched: int = 0
    no_logs: int = 0
    parse_errors: int = 0
    rederived: int = 0


def netstats_s3_uri(match_id: int) -> str:
    return f"{replay_files.s3_root}netstats/{match_id}.zip"


def load_logs_zip(
    client: CncstatsClient,
    store: s3_store.S3Store,
    match_id: int,
    save: bool = True,
) -> bytes | None:
    """cncstats first (it may have more players' logs by now), our S3 copy if it has none."""
    zip_bytes = client.get_logs_zip(match_id)
    if zip_bytes is not None:
        if save:
            store.write_bytes(netstats_s3_uri(match_id), zip_bytes)
        return zip_bytes
    try:
        return store.read_bytes(netstats_s3_uri(match_id))
    except FileNotFoundError:
        return None


def _store(repo: NetstatsRepo, match_id: int, zip_bytes: bytes, attempts: int) -> str:
    try:
        summary = summarize(parse_match_netstats(zip_bytes, match_id))
    except Exception:
        logger.exception("netstats parse failed", match_id=match_id)
        repo.save(match_id, PARSE_ERROR, PARSER_VERSION, None, attempts)
        return PARSE_ERROR
    if not summary.roster:
        repo.save(match_id, NO_LOGS, PARSER_VERSION, None, attempts)
        return NO_LOGS
    repo.save(match_id, OK, PARSER_VERSION, summary, attempts)
    return OK


def sync_netstats(
    repo: NetstatsRepo,
    client: CncstatsClient,
    store: s3_store.S3Store,
    now: datetime | None = None,
) -> SyncResult:
    result = SyncResult()
    since = (now or datetime.now(UTC)) - LOOKBACK
    # One match at a time: a parse holds a whole log zip in memory.
    for match_id in repo.matches_to_fetch(since, MAX_ATTEMPTS, MAX_PER_RUN):
        attempts = repo.attempts(match_id) + 1
        try:
            zip_bytes = load_logs_zip(client, store, match_id)
        except Exception:
            logger.exception("netstats fetch failed", match_id=match_id)
            repo.session.rollback()
            continue
        if zip_bytes is None:
            repo.save(match_id, NO_LOGS, PARSER_VERSION, None, attempts)
            result.no_logs += 1
            continue
        status = _store(repo, match_id, zip_bytes, attempts)
        result.fetched += status == OK
        result.no_logs += status == NO_LOGS
        result.parse_errors += status == PARSE_ERROR

    for match_id in repo.stale_rows(PARSER_VERSION, MAX_PER_RUN):
        try:
            zip_bytes = load_logs_zip(client, store, match_id)
        except Exception:
            logger.exception("netstats refetch failed", match_id=match_id)
            repo.session.rollback()
            continue
        if zip_bytes is None:
            # Neither source has the logs any more; keep what an old parser stored.
            continue
        _store(repo, match_id, zip_bytes, repo.attempts(match_id))
        result.rederived += 1
    logger.info("netstats sync done", **vars(result))
    return result
