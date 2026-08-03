"""Syncs bracket match scheduling to Discord Guild Scheduled Events.

Requires a bot (not the OAuth login app in ``oauth.py``, nor the send-only
``notify.py`` webhook - neither can manage guild events) invited to the
target server with the "Manage Events" permission. Configured via
``DISCORD_BOT_TOKEN`` / ``DISCORD_GUILD_ID`` / ``DISCORD_VOICE_CHANNEL_ID``;
``is_configured()`` is false (and ``sync_match_event`` a no-op) until all
three are set.

Best-effort, same contract as ``notify.py``: a Discord outage must never
break saving a match's schedule - failures are logged and the caller keeps
whatever event id it already had.
"""

import os
from datetime import datetime, timedelta

import httpx
import structlog

logger = structlog.get_logger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
VOICE_CHANNEL_ID = os.environ.get("DISCORD_VOICE_CHANNEL_ID")

_TIMEOUT = 10.0
# Matches Agenda.tsx's googleCalendarUrl default: no per-match duration is
# tracked, so a fixed 1-hour block is a placeholder rather than a precise end time.
_DEFAULT_DURATION = timedelta(hours=1)

_ENTITY_TYPE_VOICE = 2
_PRIVACY_LEVEL_GUILD_ONLY = 2


def is_configured() -> bool:
    return bool(BOT_TOKEN and GUILD_ID and VOICE_CHANNEL_ID)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bot {BOT_TOKEN}"}


def sync_match_event(
    *,
    existing_event_id: str | None,
    scheduled_at: datetime | None,
    name: str,
) -> str | None:
    """Create, reschedule, or cancel the Discord event for one bracket match
    so it mirrors ``scheduled_at``. Returns the event id to persist (None
    once cleared). No-op (returns ``existing_event_id`` unchanged) when not
    configured, or when a Discord call fails.
    """
    if not is_configured():
        return existing_event_id

    try:
        if scheduled_at is None:
            if existing_event_id:
                _cancel_event(existing_event_id)
            return None
        if existing_event_id:
            return _update_event(existing_event_id, scheduled_at, name)
        return _create_event(scheduled_at, name)
    except Exception:
        logger.exception("discord scheduled event sync failed", name=name)
        return existing_event_id


def _create_event(scheduled_at: datetime, name: str) -> str:
    resp = httpx.post(
        f"{DISCORD_API_BASE}/guilds/{GUILD_ID}/scheduled-events",
        headers=_headers(),
        json={
            "name": name,
            "privacy_level": _PRIVACY_LEVEL_GUILD_ONLY,
            "scheduled_start_time": scheduled_at.isoformat(),
            "scheduled_end_time": (scheduled_at + _DEFAULT_DURATION).isoformat(),
            "entity_type": _ENTITY_TYPE_VOICE,
            "channel_id": VOICE_CHANNEL_ID,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return str(resp.json()["id"])


def _update_event(event_id: str, scheduled_at: datetime, name: str) -> str:
    resp = httpx.patch(
        f"{DISCORD_API_BASE}/guilds/{GUILD_ID}/scheduled-events/{event_id}",
        headers=_headers(),
        json={
            "name": name,
            "scheduled_start_time": scheduled_at.isoformat(),
            "scheduled_end_time": (scheduled_at + _DEFAULT_DURATION).isoformat(),
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return event_id


def _cancel_event(event_id: str) -> None:
    resp = httpx.delete(
        f"{DISCORD_API_BASE}/guilds/{GUILD_ID}/scheduled-events/{event_id}",
        headers=_headers(),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
