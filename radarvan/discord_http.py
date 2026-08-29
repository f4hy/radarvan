"""Shared HTTP clients for the Discord calls this app makes.

``notify.py`` (the ``NOTIFY_WEB_HOOK`` webhook) and ``discord_events.py`` (the
bot API at ``discord.com/api/v10``) hit the *same origin*, so one client's
per-origin connection pool serves both. That matters for the sync path:
``MatchRepo.register_match`` notifies per match and ``matches.register_matches``
loops, so a scrape that lands 20 games used to mean 20 connect + TLS handshake
+ teardown cycles against discord.com. Pooled, it is one connection - httpx2's
``keepalive_expiry`` is 5s and those calls are sub-second apart.

Deliberately scoped to Discord rather than shared app-wide. A single global
client would have to carry one default timeout for services whose policies
differ by two orders of magnitude (gentool's scrape allows 600s, these allow
10), and ``max_connections`` is one budget across every origin in a client, so
the scrape and a webhook post would share it. Separate clients cost ~4 kB each
once the first has paid for the SSL machinery - measured, not assumed.

Neither caller sets client-level auth: the webhook's token is in its URL and
the bot token is a per-request ``Authorization`` header, so no credential
crosses between them. ``NOTIFY_WEB_HOOK`` is configurable and need not point at
Discord - if it doesn't, the pool simply keys that origin separately and
nothing else changes.
"""

from functools import cache

import httpx2

# Both callers are best-effort: a Discord outage must never stall a request or
# a scheduler job, so the timeout is short and the same for each.
TIMEOUT = 10.0


@cache
def client() -> httpx2.Client:
    """Process-wide sync client for Discord calls."""
    return httpx2.Client(timeout=TIMEOUT)


@cache
def async_client() -> httpx2.AsyncClient:
    """Process-wide async client, created lazily on first use (and thereby
    bound to the app's single event loop - same pattern as radarvan.oauth)."""
    return httpx2.AsyncClient(timeout=TIMEOUT)
