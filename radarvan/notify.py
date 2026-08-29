"""Posts notification messages to a configured webhook (``NOTIFY_WEB_HOOK``).

Four entry points with the same best-effort contract (a webhook outage must
never break the caller): ``notify`` for sync code, ``notify_async`` for async
code - it does the HTTP call natively on the event loop, so callers don't need
to wrap ``notify`` in ``asyncio.to_thread`` themselves - ``notify_background``
for async code that shouldn't wait for the webhook at all, and
``notify_throttled`` for events a hostile or broken client can produce in bulk.
"""

import asyncio
import os
import structlog

from .discord_http import async_client, client
from .rate_limit import InMemoryRateLimitStore, RateLimitStore

logger = structlog.get_logger(__name__)
WEB_HOOK_ENV = "NOTIFY_WEB_HOOK"

WEB_HOOK = os.environ.get(WEB_HOOK_ENV)


def notify(message: str) -> None:
    """Best-effort: a webhook outage must never break the caller."""
    if not WEB_HOOK:
        logger.warning("web hook not set, skipping notify", message=message)
        return
    try:
        client().post(WEB_HOOK, json={"content": message})
    except Exception:
        logger.exception("notify webhook failed", message=message)


async def notify_async(message: str) -> None:
    """Async ``notify``: same best-effort contract, awaitable on the event loop."""
    if not WEB_HOOK:
        logger.warning("web hook not set, skipping notify", message=message)
        return
    try:
        await async_client().post(WEB_HOOK, json={"content": message})
    except Exception:
        logger.exception("notify webhook failed", message=message)


# Strong refs to in-flight fire-and-forget tasks: asyncio only holds a weak
# reference to a running task, so without this the webhook call can be garbage
# collected mid-await.
_background_tasks: set[asyncio.Task[None]] = set()


def notify_background(message: str) -> None:
    """Schedule ``notify_async`` on the running loop without awaiting it.

    For notices that shouldn't add webhook latency to the response they
    describe - an auth rejection is reported *about* a request, not *by* it.
    Requires a running event loop (async handlers and dependencies); called
    without one it logs and drops the message rather than raising, since the
    best-effort contract applies to scheduling too. ``notify_async`` handles
    an unset webhook, so there is no need to check for one here.
    """
    try:
        task = asyncio.create_task(notify_async(message))
    except RuntimeError:
        logger.warning("no running event loop, skipping notify", message=message)
        return
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# Throttling for events a hostile or broken client can produce in bulk. Two
# limits, both served by the rate limiter's sliding-window store: one message
# per key per window, plus a ceiling across every key. The ceiling is what
# actually bounds outbound webhook traffic - per-key dedupe alone does nothing
# against a scanner sweeping distinct URLs, since every URL is a fresh key.
# Sharing one store across callers means the ceiling bounds the *total*, rather
# than giving each feature its own budget to blow.
THROTTLE_WINDOW_SECONDS = 60.0
THROTTLE_BUDGET_PER_WINDOW = 20
# "\x00" can't occur in a caller-built key, so these can't collide with one.
_BUDGET_KEY = "\x00budget"
_BUDGET_LOG_KEY = "\x00budget-log"
_throttle_store: RateLimitStore = InMemoryRateLimitStore()


def notify_throttled(key: str, message: str) -> None:
    """``notify_background``, at most once per ``key`` and within a global budget.

    ``key`` identifies the *kind* of event being reported (who, where, what
    outcome) so that a client retrying one rejected call is reported once
    rather than once per attempt.
    """
    if not _throttle_store.check(key, 1, THROTTLE_WINDOW_SECONDS).allowed:
        return
    if not _throttle_store.check(
        _BUDGET_KEY, THROTTLE_BUDGET_PER_WINDOW, THROTTLE_WINDOW_SECONDS
    ).allowed:
        # Throttle the "we're throttling" line too: it fires on every dropped
        # message, which is precisely when volume is the problem.
        if _throttle_store.check(_BUDGET_LOG_KEY, 1, THROTTLE_WINDOW_SECONDS).allowed:
            logger.warning("notify budget exhausted, dropping messages", key=key)
        return
    notify_background(message)
