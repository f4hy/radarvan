"""Posts notification messages to a configured webhook (``NOTIFY_WEB_HOOK``)."""

import httpx
import os
import structlog

logger = structlog.get_logger(__name__)
WEB_HOOK_ENV = "NOTIFY_WEB_HOOK"

WEB_HOOK = os.environ.get(WEB_HOOK_ENV)


def notify(message: str) -> None:
    """Best-effort: a webhook outage must never break the caller."""
    if not WEB_HOOK:
        logger.warning("web hook not set, skipping notify", message=message)
        return
    try:
        httpx.post(WEB_HOOK, json={"content": message}, timeout=10.0)
    except Exception:
        logger.exception("notify webhook failed", message=message)
