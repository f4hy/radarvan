"""``log_time`` context manager that logs an event and its elapsed wall-clock time."""

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog
from structlog.stdlib import BoundLogger


@contextmanager
def log_time(
    message: str, logger: BoundLogger | None = None, **kwargs: Any
) -> Generator[None]:
    """
    Context manager that logs an event and the elapsed time.

    Extra kwargs are bound onto the log line, e.g.
    ``log_time("reading json", logger, path=json_path)``.
    """
    if logger is None:
        logger = structlog.get_logger()
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        logger.info(message, elapsed_s=round(elapsed, 4), **kwargs)
