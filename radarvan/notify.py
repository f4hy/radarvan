"""Posts notification messages to a configured webhook (``NOTIFY_WEB_HOOK``)."""

import httpx
import os
import structlog

logger = structlog.get_logger(__name__)
WEB_HOOK_ENV = "NOTIFY_WEB_HOOK"

WEB_HOOK = os.environ.get(WEB_HOOK_ENV)


def notify(message: str) -> None:
    if not WEB_HOOK:
        logger.warning("web hook not set, skipping notify", message=message)
        return
    httpx.post(WEB_HOOK, json={"content": message})
