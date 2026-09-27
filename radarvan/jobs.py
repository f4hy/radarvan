"""Scheduled jobs, run by Heroku Scheduler on one-off dynos: ``python -m radarvan.jobs <job>``."""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

import structlog

from . import schedule
from .db_utils import DatabaseManager
from .dependencies import IS_DEV, db_manager
from .logging_config import configure_logging
from .notify import notify_async

logger = structlog.get_logger(__name__)

type Step = Callable[[DatabaseManager], Awaitable[None]]

# Steps within a job run in order, and a failed step doesn't stop the next.
# Nothing retries: Heroku Scheduler doesn't, and every job is safe to rerun by
# hand from the command in the failure notice. Scheduler times are UTC.
JOBS: dict[str, list[Step]] = {
    # 01:00, 07:00, 13:00, 19:00
    "update_games": [schedule.update_games],
    # 04:00. Profiles second: the superlatives pass leaves match_details_cache warm.
    "nightly_stats": [
        schedule.compute_and_save_superlatives,
        schedule.compute_and_save_player_profiles,
    ],
    # 11:00, the first slot after the 5am US Eastern game-night rollover in both
    # EST and EDT. Blurbs after the recap, so a recap failure can't take them down.
    "game_night": [
        schedule.compute_game_night_summary,
        schedule.compute_match_blurbs,
    ],
}


def _failed_message(job: str, step: str, exc: BaseException) -> str:
    detail = f"{type(exc).__name__}: {exc}"[:500]
    return (
        f"Scheduled job `{job}` failed in `{step}`: {detail}\n"
        f"Rerun: `heroku run python -m radarvan.jobs {job} -a radarvan`"
    )


async def run(job: str, manager: DatabaseManager) -> bool:
    ok = True
    for step in JOBS[job]:
        logger.info("job step starting", job=job, step=step.__name__)
        try:
            await step(manager)
        except Exception as exc:
            logger.exception("job step failed", job=job, step=step.__name__)
            await notify_async(_failed_message(job, step.__name__, exc))
            ok = False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m radarvan.jobs")
    parser.add_argument("job", choices=JOBS)
    job = parser.parse_args().job
    configure_logging(dev=IS_DEV)
    if not asyncio.run(run(job, db_manager)):
        sys.exit(1)


if __name__ == "__main__":
    main()
