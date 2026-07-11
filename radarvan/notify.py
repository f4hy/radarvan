"""Posts notification messages to a configured webhook (``NOTIFY_WEB_HOOK``).

Two entry points with the same best-effort contract (a webhook outage must
never break the caller): ``notify`` for sync code, ``notify_async`` for async
code - it does the HTTP call natively on the event loop, so callers don't need
to wrap ``notify`` in ``asyncio.to_thread`` themselves.
"""

from functools import cache

import httpx
import os
import structlog

logger = structlog.get_logger(__name__)
WEB_HOOK_ENV = "NOTIFY_WEB_HOOK"

WEB_HOOK = os.environ.get(WEB_HOOK_ENV)

_TIMEOUT = 10.0


def notify(message: str) -> None:
    """Best-effort: a webhook outage must never break the caller."""
    if not WEB_HOOK:
        logger.warning("web hook not set, skipping notify", message=message)
        return
    try:
        httpx.post(WEB_HOOK, json={"content": message}, timeout=_TIMEOUT)
    except Exception:
        logger.exception("notify webhook failed", message=message)


@cache
def _async_client() -> httpx.AsyncClient:
    """Process-wide async client, created lazily on first use (and thereby
    bound to the app's single event loop - same pattern as radarvan.oauth)."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


async def notify_async(message: str) -> None:
    """Async ``notify``: same best-effort contract, awaitable on the event loop."""
    if not WEB_HOOK:
        logger.warning("web hook not set, skipping notify", message=message)
        return
    try:
        await _async_client().post(WEB_HOOK, json={"content": message})
    except Exception:
        logger.exception("notify webhook failed", message=message)
