"""Rate-limit storage abstraction.

The HTTP concern (radarvan.middleware.RateLimitMiddleware) is decoupled from
*where* hit counts live via the `RateLimitStore` protocol. Today the only
backend is in-memory (per worker process). A shared backend — Redis or the DB —
can be dropped in later by implementing the same `check` method, e.g. a Redis
sorted-set sliding window (ZADD/ZREMRANGEBYSCORE/ZCARD) or an INCR-with-expiry
fixed window. The middleware passes the window in on each call, so a backend
never hardcodes it.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of recording one request against a key.

    `retry_after` is the seconds until a slot frees (0 when allowed) and carries
    NO jitter — the caller adds jitter when forming the Retry-After header so the
    store stays a pure counter.
    """

    allowed: bool
    limit: int
    remaining: int
    retry_after: float


class RateLimitStore(Protocol):
    """Records a request against `key` and decides if it's within `limit`.

    Implementations must be safe to call concurrently and should treat the
    record-and-decide as a single atomic step (so two simultaneous requests
    can't both slip past the limit).
    """

    def check(self, key: str, limit: int, window_seconds: float) -> RateLimitDecision:
        ...


class InMemoryRateLimitStore:
    """Per-process sliding-window store: a deque of hit timestamps per key.

    Accurate within one worker; not shared across workers/dynos (each enforces
    its own share — acceptable for a single web dyno, and a safe degradation if
    scaled out). Thread-safe because sync endpoints run in uvicorn's threadpool.
    Idle keys are swept periodically so memory doesn't grow with one-off clients.
    """

    def __init__(self, prune_interval_seconds: float = 60.0) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._prune_interval = prune_interval_seconds
        self._last_prune = time.monotonic()

    def check(self, key: str, limit: int, window_seconds: float) -> RateLimitDecision:
        now = time.monotonic()
        with self._lock:
            self._maybe_prune(now, window_seconds)
            hits = self._hits[key]
            cutoff = now - window_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                # Oldest hit leaving the window frees the next slot.
                retry_after = max(0.0, (hits[0] + window_seconds) - now)
                return RateLimitDecision(
                    allowed=False, limit=limit, remaining=0, retry_after=retry_after
                )
            hits.append(now)
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - len(hits)),
                retry_after=0.0,
            )

    def _maybe_prune(self, now: float, window_seconds: float) -> None:
        """Drop buckets whose most recent hit has aged out of the window."""
        if now - self._last_prune < self._prune_interval:
            return
        cutoff = now - window_seconds
        stale = [k for k, dq in self._hits.items() if not dq or dq[-1] <= cutoff]
        for k in stale:
            del self._hits[k]
        self._last_prune = now
