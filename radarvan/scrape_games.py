from .db_utils import DatabaseManager, ReplayManager
from typing import Any
import asyncio
import httpx2
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
import os
from datetime import UTC, datetime, timedelta
import structlog
from . import player_ids
from functools import cache
from cachetools import TTLCache
from cachetools_async import cached
from . import replay_files
from .logging_config import configure_logging

logger = structlog.get_logger(__name__)
BASE = "https://www.gentool.net/data/zh/"
TIMEOUT = 600.0


@cache
def async_client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(timeout=600.0)


@cache
def _request_semaphore() -> asyncio.Semaphore:
    """Shared semaphore limiting concurrent scrape requests.

    Built lazily (and cached) so all callers share one limiter; a per-call
    ``asyncio.Semaphore(4)`` would never actually cap concurrency.
    """
    return asyncio.Semaphore(4)


@cached(cache=TTLCache(maxsize=1024, ttl=600))
async def get_url(url: str) -> httpx2.Response:
    client = async_client()
    logger.debug("getting url", url=url)
    async with _request_semaphore():
        response = await client.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    logger.debug(
        "finished reading url", url=url, elapsed_s=response.elapsed.total_seconds()
    )
    if response.elapsed.total_seconds() > 2:
        logger.debug("waiting", seconds=response.elapsed.total_seconds() * 4)
        await asyncio.sleep(response.elapsed.total_seconds() * 4)
    return response


def generate_directories(n_days: int, base_path: str = ".") -> Any:
    """The last ``n_days`` date-path strings (``YYYY_MM_Month/DD_Day``), oldest first."""
    current_date = datetime.now(UTC)

    base = Path(base_path)
    base.mkdir(exist_ok=True)

    created_dirs = []

    for i in range(-1, n_days):
        date = current_date - timedelta(days=i)
        year_month = date.strftime("%Y_%m_%B")
        day_name = date.strftime("%d_%A")
        full_path = base / year_month / day_name
        created_dirs.append(str(full_path))

    return reversed(created_dirs)


async def matching_links(base_url: str, patterns: list[str]) -> list[str]:
    """URLs from an Apache directory listing whose href matches one of ``patterns``."""
    logger.debug("finding links", patterns=patterns, base_url=base_url)

    try:
        response = await get_url(base_url)
    except httpx2.ReadTimeout:
        logger.warning("timed out reading", base_url=base_url)
        return []
    except Exception as e:
        logger.warning("error reading", base_url=base_url, error=repr(e))
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for link in soup.find_all("a", href=True):
        href = str(link["href"])

        if href in ["../", "../"]:
            continue

        if any((p in href) for p in patterns):
            logger.debug("found href", href=href)
            file_url = urljoin(base_url, href)
            links.append(file_url)
    logger.debug("found links", links=links)
    return links


async def get_player_dirs(root: str) -> list[str]:
    user_ids = list(player_ids.PLAYERS.values())
    dirs = await matching_links(root, user_ids)
    return [
        d
        for d in dirs
        if not any(blocked in d for blocked in player_ids.BLOCKED_SCRAPE_DIRS)
    ]


async def search_dates(days: int, base: str) -> list[list[str]]:
    dir_list_coro = []
    for d in generate_directories(days):
        date_path = f"{base}{d}/"
        logger.debug("searching", date_path=date_path)
        dir_list_coro.append(get_player_dirs(date_path))

    return await asyncio.gather(*dir_list_coro)


async def search_replays(urls_to_list: list[str]) -> list[list[str]]:
    dir_list_coro = []
    for url in urls_to_list:
        logger.debug("searching", url=url)
        dir_list_coro.append(matching_links(url, [".rep"]))

    return await asyncio.gather(*dir_list_coro)


async def get_replay_urls(
    days: int,
    base: str,
    replay_manager: ReplayManager,
) -> list[Any]:
    existing_paths = replay_manager.already_scraped()
    all_paths = await search_dates(days, base)
    all_replay_paths = []
    for paths in all_paths:
        replay_paths = await search_replays(paths)
        all_replay_paths.append(replay_paths)
        for paths in replay_paths:
            for p in paths:
                if p not in existing_paths:
                    try:
                        # parse_replay is blocking (S3 + cncstats HTTP); keep it
                        # off the event loop. Sequential, so the shared session
                        # is safe.
                        await asyncio.to_thread(
                            replay_files.parse_replay, p, replay_manager
                        )
                    except Exception as e:
                        # One unparseable replay must not abandon the rest of
                        # the run. A failed flush leaves the session in a
                        # rolled-back state, so every later statement would
                        # raise PendingRollbackError without this rollback.
                        logger.warning(
                            "failed to parse scraped replay", path=p, error=repr(e)
                        )
                        replay_manager.session.rollback()
    return all_replay_paths


if __name__ == "__main__":
    configure_logging(dev=True)
    pattern = "09BAC013F91C"
    conn_str = os.getenv("DATABASE_URL")
    if conn_str is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(conn_str)
    with db_manager.get_session() as session:
        replay_manager = ReplayManager(session)

        all_paths = asyncio.run(get_replay_urls(0, BASE, replay_manager))
        logger.debug("all paths", all_paths=all_paths)
        with Path("replay_paths.txt").open("w") as f:
            for paths in all_paths:
                for p in paths:
                    for i in p:
                        f.write(f'"{i}"')
                        f.write(",\n")
