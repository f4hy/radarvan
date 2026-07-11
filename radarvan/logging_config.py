"""Structlog + stdlib logging configuration.

Our code logs via structlog; third-party libraries (uvicorn, sqlalchemy,
apscheduler, ...) log via stdlib logging. Both are rendered through the same
``ProcessorFormatter`` so output is consistent and contextvars bound in the
request middleware (``request_id``, ``client``) are merged into every line.
"""

import json
import logging
from datetime import datetime
from typing import Any

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

# Dev only: shorten the noisier level names so the level column stays narrow.
_LEVEL_SHORT = {"critical": "crit", "exception": "exc", "warning": "warn"}


def _stringify_keys(value: Any) -> Any:
    """Recursively coerce dict keys to str so json.dumps can't choke on them."""
    if isinstance(value, dict):
        return {str(k): _stringify_keys(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_stringify_keys(v) for v in value]
    return value


def _json_serializer(obj: Any, **kwargs: Any) -> str:
    """json.dumps with default=str, falling back to key-coercion.

    ``default=str`` only stringifies non-serializable *values*; a dict keyed by
    a tuple/enum still raises. The fallback path keeps the log line instead of
    dropping it. We override any ``default`` JSONRenderer injected with ``str``.
    """
    kwargs["default"] = str
    try:
        return json.dumps(obj, **kwargs)
    except TypeError:
        return json.dumps(_stringify_keys(obj), **kwargs)


def _dev_timestamp(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Local time of day with millisecond precision (no date) for dev consoles."""
    event_dict["timestamp"] = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # noqa: DTZ005 (intentionally local, not UTC)
    return event_dict


def _shorten_level(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    level = event_dict.get("level")
    if level in _LEVEL_SHORT:
        event_dict["level"] = _LEVEL_SHORT[level]
    return event_dict


def configure_logging(dev: bool = False) -> None:
    """Configure structlog and route stdlib logging through it.

    ``dev=True`` renders a colorized, human-friendly console; otherwise emits
    one JSON object per line (good for grepping Heroku logs by request_id).
    """
    timestamper: Processor = (
        _dev_timestamp if dev else structlog.processors.TimeStamper(fmt="iso")
    )
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
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
        default_styles = structlog.dev.ConsoleRenderer.get_default_level_styles()
        level_styles = {
            "crit": default_styles["critical"],
            "exc": default_styles["exception"],
            "error": default_styles["error"],
            "warn": default_styles["warning"],
            "info": default_styles["info"],
            "debug": default_styles["debug"],
        }
        # Reorder the default columns so the logger name sits right after the
        # level, before the event message. We reuse the columns the renderer
        # builds (which already bake in level_styles) and just resequence them.
        # pad_event_to=20 keeps a modest fixed-width event column.
        base = structlog.dev.ConsoleRenderer(level_styles=level_styles, pad_event_to=20)
        cols = {c.key: c for c in base.columns}
        console = structlog.dev.ConsoleRenderer(
            columns=[
                cols[""],
                cols["timestamp"],
                cols["level"],
                cols["logger"],
                cols["logger_name"],
                cols["event"],
            ]
        )
        render_processors: list[Processor] = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _shorten_level,
            console,
        ]
    else:
        render_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(serializer=_json_serializer),
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

    # uvicorn/gunicorn install their own handlers on named loggers with
    # propagate=False, so their output would otherwise bypass this formatter.
    # Redirect them through the root handler for consistent (JSON in prod) output.
    for name in (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "gunicorn.error",
        "gunicorn.access",
    ):
        named = logging.getLogger(name)
        named.handlers.clear()
        named.propagate = True
