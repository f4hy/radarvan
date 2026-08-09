"""Vocab + feature encoding: ``MatchInfo`` -> plain-int ``EncodedMatch``.

Torch-free on purpose so the snapshot/split steps can build and freeze the vocab
without importing torch. Tensorisation happens in ``ml/dataset.py``.

Conventions:
- Index 0 is always the ``UNK`` slot for every categorical vocab. Players/maps
  unseen at train time fall through to ``UNK`` at dev/inference time, mirroring
  production where new players and maps appear.
- General/faction vocabs are fixed from the ``api_types`` enums (closed set), so
  they are identical across snapshots and never depend on the data.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from radarvan import player_ids
from radarvan.api_types import General, MatchInfo
from radarvan.game_composition import RosterSlot

from .map_features import N_MAP_FEATURES, normalize_map_name

UNK = 0

# Closed categorical sets from the enums (recognised values only; -1/UNRECOGNIZED
# falls through to the UNK slot).
_GENERALS: list[int] = [g.value for g in General if g.value >= 0]
# Faction == general // 4 (USA 0-3, China 4-7, GLA 8-11).
_FACTIONS: list[int] = [0, 1, 2]
# Starting positions we bother to model when enabled; anything else -> UNK.
_MAX_START_POS = 8


def faction_of(general: int) -> int:
    """USA/China/GLA family for a general value, or -1 if unrecognised."""
    if general < 0:
        return -1
    return general // 4


def _fixed_index(values: list[int]) -> dict[int, int]:
    """Map a closed set of int categories to contiguous indices after UNK=0."""
    return {v: i + 1 for i, v in enumerate(values)}


@dataclass(slots=True)
class Vocab:
    """Frozen lookup tables. Built from the *training* split only."""

    player: dict[str, int]  # resolved player name -> idx (UNK=0)
    map: dict[str, int]  # map name -> idx (UNK=0); used only by the embedding path
    fmt: dict[str, int]  # composition category -> idx (UNK=0)
    general: dict[int, int]  # General value -> idx (closed)
    faction: dict[int, int]  # faction value -> idx (closed)

    # Numeric map features (the alternative to the `map` embedding). Raw (log-
    # scaled, unstandardised) vectors keyed by normalized map name, plus the
    # train-set standardisation stats. See ml/map_features.py.
    map_feat_raw: dict[str, list[float]] = field(default_factory=dict)
    map_feat_mean: list[float] = field(default_factory=lambda: [0.0] * N_MAP_FEATURES)
    map_feat_std: list[float] = field(default_factory=lambda: [1.0] * N_MAP_FEATURES)

    @property
    def n_players(self) -> int:
        return len(self.player) + 1

    @property
    def n_maps(self) -> int:
        return len(self.map) + 1

    @property
    def n_formats(self) -> int:
        return len(self.fmt) + 1

    @property
    def n_generals(self) -> int:
        return len(self.general) + 1

    @property
    def n_factions(self) -> int:
        return len(self.faction) + 1

    def player_idx(self, resolved_name: str) -> int:
        return self.player.get(resolved_name, UNK)

    def map_idx(self, name: str) -> int:
        return self.map.get(name, UNK)

    def map_feature_vector(self, name: str) -> list[float]:
        """Standardised numeric features for a map name.

        Falls back to the train mean (-> standardised zeros) for any map with no
        geometry — i.e. "an average map", not a degenerate UNK. Generalises to
        maps unseen in training as long as they have a MapData row.
        """
        raw = self.map_feat_raw.get(normalize_map_name(name))
        if raw is None:
            return [0.0] * N_MAP_FEATURES
        return [
            (raw[i] - self.map_feat_mean[i]) / (self.map_feat_std[i] or 1.0)
            for i in range(N_MAP_FEATURES)
        ]

    def fmt_idx(self, name: str | None) -> int:
        return self.fmt.get(name or "", UNK)

    def general_idx(self, general: int) -> int:
        return self.general.get(general, UNK)

    def faction_idx(self, general: int) -> int:
        return self.faction.get(faction_of(general), UNK)

    def to_json(self) -> dict[str, object]:
        return {
            "player": self.player,
            "map": self.map,
            "fmt": self.fmt,
            # general/faction are closed sets; stored for completeness.
            "general": {str(k): v for k, v in self.general.items()},
            "faction": {str(k): v for k, v in self.faction.items()},
            "map_feat_raw": self.map_feat_raw,
            "map_feat_mean": self.map_feat_mean,
            "map_feat_std": self.map_feat_std,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json(), indent=2, sort_keys=True))

    @classmethod
    def load(cls, path: Path) -> Vocab:
        raw = json.loads(path.read_text())
        n = N_MAP_FEATURES
        return cls(
            player={str(k): int(v) for k, v in raw["player"].items()},
            map={str(k): int(v) for k, v in raw["map"].items()},
            fmt={str(k): int(v) for k, v in raw["fmt"].items()},
            general={int(k): int(v) for k, v in raw["general"].items()},
            faction={int(k): int(v) for k, v in raw["faction"].items()},
            map_feat_raw={
                str(k): [float(x) for x in v]
                for k, v in raw.get("map_feat_raw", {}).items()
            },
            map_feat_mean=[float(x) for x in raw.get("map_feat_mean", [0.0] * n)],
            map_feat_std=[float(x) for x in raw.get("map_feat_std", [1.0] * n)],
        )


def resolved_real_players(match: MatchInfo) -> list[tuple[str, RosterSlot]]:
    """(resolved_name, slot) for every competitor on a real team.

    Goes through MatchRoster so training and serving classify observers and AI
    the same way the rest of the backend does - see CLAUDE.md.
    """
    return [
        (player_ids.resolve_player_name(p.name, p.color), p)
        for p in match.roster().participants
    ]


def build_vocab(
    matches: Iterable[MatchInfo],
    map_feat_table: dict[str, list[float]] | None = None,
) -> Vocab:
    """Freeze the vocab from (training) matches. Sorted for determinism.

    ``map_feat_table`` (normalized-name -> raw features, from MapData over *all*
    maps) is stored as-is for serving; the standardisation mean/std are computed
    from only the maps that appear in these (training) matches, so normalisation
    reflects the training distribution.
    """
    players: set[str] = set()
    maps: set[str] = set()
    formats: set[str] = set()
    for m in matches:
        for name, _ in resolved_real_players(m):
            players.add(name)
        maps.add(m.map)
        if m.composition is not None:
            formats.add(m.composition.category)

    table = map_feat_table or {}
    mean, std = _map_feat_stats(maps, table)
    return Vocab(
        player={name: i + 1 for i, name in enumerate(sorted(players))},
        map={name: i + 1 for i, name in enumerate(sorted(maps))},
        fmt={name: i + 1 for i, name in enumerate(sorted(formats))},
        general=_fixed_index(_GENERALS),
        faction=_fixed_index(_FACTIONS),
        map_feat_raw=table,
        map_feat_mean=mean,
        map_feat_std=std,
    )


def _map_feat_stats(
    train_maps: Iterable[str], table: dict[str, list[float]]
) -> tuple[list[float], list[float]]:
    """Per-feature mean/std over the training maps that have geometry."""
    vecs = [
        table[key]
        for key in {normalize_map_name(m) for m in train_maps}
        if key in table
    ]
    if not vecs:
        return [0.0] * N_MAP_FEATURES, [1.0] * N_MAP_FEATURES
    n = len(vecs)
    mean = [sum(v[i] for v in vecs) / n for i in range(N_MAP_FEATURES)]
    std = [
        (sum((v[i] - mean[i]) ** 2 for v in vecs) / n) ** 0.5 or 1.0
        for i in range(N_MAP_FEATURES)
    ]
    return mean, std


@dataclass(slots=True)
class EncodedPlayer:
    player: int
    general: int
    faction: int
    start_pos: int  # 0 == UNK/unknown


@dataclass(slots=True)
class EncodedMatch:
    """A 2-team match encoded to plain ints. team_a won iff ``label == 1``."""

    match_id: int
    map: int
    map_feat: list[float]  # standardised numeric map features (map-feature path)
    fmt: int
    team_a: list[EncodedPlayer]
    team_b: list[EncodedPlayer]
    label: int
    duration_minutes: float


def _start_pos_idx(pos: int | None) -> int:
    if pos is None or pos < 0 or pos > _MAX_START_POS:
        return UNK
    return pos + 1


def encode_match(match: MatchInfo, vocab: Vocab) -> EncodedMatch | None:
    """Encode a match for training. Returns None if it isn't a usable 2-team game.

    Team-order is canonicalised by ascending team id; the model head is
    antisymmetric so this choice does not bias the prediction.
    """
    teams: dict[int, list[EncodedPlayer]] = {}
    for name, p in resolved_real_players(match):
        teams.setdefault(p.team, []).append(
            EncodedPlayer(
                player=vocab.player_idx(name),
                general=vocab.general_idx(int(p.general)),
                faction=vocab.faction_idx(int(p.general)),
                start_pos=_start_pos_idx(p.starting_position),
            )
        )
    if len(teams) != 2:
        return None
    team_ids = sorted(teams)
    a_id, b_id = team_ids
    winner = int(match.winning_team)
    if winner not in (a_id, b_id):
        return None
    if not teams[a_id] or not teams[b_id]:
        return None
    return EncodedMatch(
        match_id=match.id,
        map=vocab.map_idx(match.map),
        map_feat=vocab.map_feature_vector(match.map),
        fmt=vocab.fmt_idx(match.composition.category if match.composition else None),
        team_a=teams[a_id],
        team_b=teams[b_id],
        label=1 if winner == a_id else 0,
        duration_minutes=match.duration_minutes,
    )
