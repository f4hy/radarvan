"""Small, dependency-free helpers shared across replay-extraction modules.

This module deliberately has no internal radarvan imports so it can be safely
imported by `match_details.py`, `build_order.py`, `timeline_events.py`, and
`stats_extraction.py` without creating cycles.
"""

from __future__ import annotations

import re

FACTION_PREFIX_RE = re.compile(r"^(China|America|GLA)")


def clean_object_name(name: str) -> str:
    """Strip per-general (e.g. ``Chem_``) and side (``China`` / ``America`` /
    ``GLA``) prefixes from a cncstats object name."""
    if "_" in name:
        name = name.split("_", 1)[1]
    return FACTION_PREFIX_RE.sub("", name)


def is_initial_seed_frame(frame: int) -> bool:
    """True for events the engine emits at game start (frame ≤ 0) — game-spawned
    Command Center / Dozer / Worker build events and the initial rank-1
    seed. We don't want them in the build-order or timeline views."""
    return frame <= 0
