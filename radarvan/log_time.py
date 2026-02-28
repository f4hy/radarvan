import time
from collections.abc import Generator
from contextlib import contextmanager
import logging


@contextmanager
def log_time(message: str, logger: logging.Logger | None = None) -> Generator[None]:
    """
    Context manager that logs a message and the elapsed time.
    """
    if logger is None:
        logger = logging.getLogger()
    start_time = time.perf_counter()
    try:
        yield
    finally:
        # Calculate elapsed time and log completion
        elapsed = time.perf_counter() - start_time
        logger.info(f"{message} - {elapsed:.4f} seconds")
