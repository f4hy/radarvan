import httpx
import os
import logging

logger = logging.getLogger(__name__)
WEB_HOOK_ENV = "NOTIFY_WEB_HOOK"

WEB_HOOK = os.environ.get(WEB_HOOK_ENV)


def notify(message: str) -> None:
    if not WEB_HOOK:
        logger.warning(f"web hook not set, skipping notify {message}")
        return
    httpx.post(WEB_HOOK, json={"content": message})
