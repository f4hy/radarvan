import time
from contextlib import contextmanager
from typing import Optional
import logging

@contextmanager
def log_time(message: str, logger: Optional[logging.Logger] = None):
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
