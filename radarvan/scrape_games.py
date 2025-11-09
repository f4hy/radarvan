from db_utils import DatabaseManager, MatchRepository, ReplayManager, StatsRepository
import asyncio
import re
import httpx  # <-- Only change needed
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
import asyncio
import httpx
import os
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import logging
import player_ids
from functools import cache
from cachetools import TTLCache
from cachetools_async import cached
import replay_files

logger = logging.getLogger(__name__)
TIMEOUT = 120.0


@cache
def async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=60.0)


@cached(cache=TTLCache(maxsize=1024, ttl=600))
async def get_url(url: str) -> httpx.Response:
    client = async_client()
    logger.info(f"Getting {url=}")
    response = await client.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    logger.info(f"Finished Reading {url=} in {response.elapsed.total_seconds()}s")
    return response


def generate_directories(n_days, base_path="."):
    """
    Generate directory structure for the last N days.

    Args:
        n_days (int): Number of days to go back
        base_path (str): Base directory path where to create the structure
    """
    # Get current date
    current_date = datetime.now()

    # Create base path if it doesn't exist
    base = Path(base_path)
    base.mkdir(exist_ok=True)

    created_dirs = []

    # Generate directories for last N days
    for i in range(n_days):
        # Calculate date for this iteration
        date = current_date - timedelta(days=i)

        # Format: YYYY_MM_MonthName
        year_month = date.strftime("%Y_%m_%B")

        # Format: DD_DayName
        day_name = date.strftime("%d_%A")

        # Create full path
        full_path = base / year_month / day_name

        # Create directory
        # full_path.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(full_path))

        # print(f"Created: {full_path}")

    return created_dirs


async def matching_links(base_url: str, patterns: list[str]):
    """
    Download files from an Apache directory listing that match a pattern.

    """
    logger.info(f"Finding links matching {patterns} from {base_url}")

    try:
        response = await get_url(base_url)
    except httpx.ReadTimeout:
        logger.info(f"Timed out reading from {base_url}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for link in soup.find_all("a", href=True):
        # print("link?", link)
        href = link["href"]

        if href in ["../", "../"]:
            continue

        if any((p in href) for p in patterns):
            print("href", href)
            file_url = urljoin(base_url, href)
            links.append(file_url)
    logger.info(f"Found {links}")
    return links
    #         filename = href.split("/")[-1]
    #         if not filename:
    #             print("NO filename?")
    #             continue
    #         print(filename)
    #         filepath = Path(download_dir) / filename

    #         print(f"Downloading: {filename}")

    #         file_response = httpx.get(file_url)
    #         file_response.raise_for_status()

    #         with open(filepath, "wb") as f:
    #             f.write(file_response.content)

    #         downloaded.append(str(filepath))
    #         print(f"  Saved to: {filepath}")

    # return downloaded


async def get_player_dirs(root: str) -> list[str]:
    user_ids = list(player_ids.PLAYERS.values())
    player_dirs = await matching_links(root, user_ids)
    return player_dirs


async def search_dates(days: int, base: str) -> list[str]:
    dir_list_coro = []
    for d in generate_directories(days):
        date_path = f"{base}{d}/"
        logger.info(f"Searching {date_path}")
        dir_list_coro.append(get_player_dirs(date_path))

    dir_lists = await asyncio.gather(*dir_list_coro)
    return dir_lists


async def search_replays(urls_to_list: str) -> list[str]:
    dir_list_coro = []
    for url in urls_to_list:
        logger.info(f"Searching {url}")
        dir_list_coro.append(matching_links(url, [".rep"]))

    dir_lists = await asyncio.gather(*dir_list_coro)
    return dir_lists


async def get_replay_urls(
    days: int,
    base: str,
    replay_manager: ReplayManager,
):
    all_paths = await search_dates(days, base)
    all_replay_paths = []
    for paths in all_paths:
        replay_paths = await search_replays(paths)
        all_replay_paths.append(replay_paths)
        for paths in replay_paths:
            for p in paths:
                replay_files.parse_replay(p, replay_manager)

    return all_replay_paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    base = "https://www.gentool.net/data/zh/"
    pattern = "09BAC013F91C"
    logging.basicConfig(level=logging.INFO)
    conn_str = os.getenv("DATABASE_URL")
    db_manager = DatabaseManager(conn_str)
    with db_manager.get_session() as session:
        replay_manager = ReplayManager(session)

        all_paths = asyncio.run(get_replay_urls(2, base, replay_manager))
        print("ALL_PATHS", all_paths)
        with open("replay_paths.txt", "w") as f:
            for paths in all_paths:
                for p in paths:
                    for i in p:
                        f.write(f'"{i}"')
                        f.write(",\n")
