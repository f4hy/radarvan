"""Structlog + stdlib logging configuration.

Our code logs via structlog; third-party libraries (uvicorn, sqlalchemy,
apscheduler, ...) log via stdlib logging. Both are rendered through the same
``ProcessorFormatter`` so output is consistent and contextvars bound in the
request middleware (``request_id``, ``client``) are merged into every line.
"""

import logging

import structlog
from structlog.typing import Processor


def configure_logging(dev: bool = False) -> None:
    """Configure structlog and route stdlib logging through it.

    ``dev=True`` renders a colorized, human-friendly console; otherwise emits
    one JSON object per line (good for grepping Heroku logs by request_id).
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if dev:
        render_processors: list[Processor] = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        render_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            # default=str so datetimes / ORM objects stringify instead of
            # raising and dropping the log line.
            structlog.processors.JSONRenderer(default=str),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=render_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    # Third-party libraries stay at INFO; in dev our own loggers drop to DEBUG.
    root.setLevel(logging.INFO)
    logging.getLogger("radarvan").setLevel(logging.DEBUG if dev else logging.INFO)
