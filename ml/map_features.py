"""Numeric map features (torch-free) — an alternative to the per-map embedding.

A per-map *name* embedding can't generalise: a map seen once (or never) in train
gets a near-UNK vector, and ~⅓ of our maps are singletons. Numeric geometry
features (size, money/player, oils/player) instead describe *what a map is like*,
so an unseen map with a typical layout is scored sensibly. See ``model_design.md``.

Three features, all derived from the stored ``MapData`` geometry payload
(``MapDataPayload``: ``extent``, ``player_starts``, ``supply``, ``tech``):

- ``log(width * height)``            — overall size
- ``log1p(len(supply) / players)``   — money sources per player
- ``log1p(len(tech)   / players)``   — oil derricks per player

The right tails are heavy (supply/player ranges 0.5..86), so each is log-scaled
here and standardised (mean/std from the train split) in ``Vocab``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

# Order is fixed: it defines the model's map_feat input layout. Don't reorder.
FEATURE_NAMES = ("log_size", "log_money_per_player", "log_oil_per_player")
N_MAP_FEATURES = len(FEATURE_NAMES)


def normalize_map_name(name: str) -> str:
    """Bridge a replay map path to a ``MapData`` key.

    Replays store ``maps/green pastures`` / ``userdata/maps/[rank] ...`` (lower,
    path-prefixed); ``MapData`` is keyed by the human name (``Green Pastures``).
    Take the basename, casefold, and collapse whitespace so the two line up.
    """
    base = name.rsplit("/", 1)[-1]
    return " ".join(base.strip().lower().split())


def raw_features_from_payload(data: Mapping[str, Any]) -> list[float] | None:
    """Compute the (log-scaled, unstandardised) feature vector for a map.

    Returns ``None`` when the geometry is unusable (no extent or no player
    starts), so the caller can fall back to the mean ("an average map").
    """
    extent = data.get("extent") or {}
    width = extent.get("width")
    height = extent.get("height")
    n_players = len(data.get("player_starts") or [])
    if not width or not height or n_players <= 0:
        return None
    n_supply = len(data.get("supply") or [])
    n_tech = len(data.get("tech") or [])
    return [
        math.log(float(width) * float(height)),
        math.log1p(n_supply / n_players),
        math.log1p(n_tech / n_players),
    ]


def build_table(rows: Iterable[tuple[str, Mapping[str, Any]]]) -> dict[str, list[float]]:
    """``{normalized_map_name: raw_features}`` for every map with usable geometry.

    ``rows`` is ``(map_name, data_payload)`` pairs straight from ``MapData``. Built
    over *all* maps (not just trained ones) so serving can score any map that has
    geometry, including ones that never appeared in training.
    """
    table: dict[str, list[float]] = {}
    for name, data in rows:
        feats = raw_features_from_payload(data)
        if feats is not None:
            table[normalize_map_name(name)] = feats
    return table
