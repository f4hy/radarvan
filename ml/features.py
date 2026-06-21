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
from dataclasses import dataclass
from pathlib import Path

from radarvan import player_ids
from radarvan.api_types import General, MatchInfo, Player

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
    map: dict[str, int]  # map name -> idx (UNK=0)
    fmt: dict[str, int]  # composition category -> idx (UNK=0)
    general: dict[int, int]  # General value -> idx (closed)
    faction: dict[int, int]  # faction value -> idx (closed)

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
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json(), indent=2, sort_keys=True))

    @classmethod
    def load(cls, path: Path) -> Vocab:
        raw = json.loads(path.read_text())
        return cls(
            player={str(k): int(v) for k, v in raw["player"].items()},
            map={str(k): int(v) for k, v in raw["map"].items()},
            fmt={str(k): int(v) for k, v in raw["fmt"].items()},
            general={int(k): int(v) for k, v in raw["general"].items()},
            faction={int(k): int(v) for k, v in raw["faction"].items()},
        )


def resolved_real_players(match: MatchInfo) -> list[tuple[str, Player]]:
    """(resolved_name, player) for real (team > 0) players in a match."""
    out: list[tuple[str, Player]] = []
    for p in match.players:
        if p.team <= 0:
            continue
        out.append((player_ids.resolve_player_name(p.name, p.color), p))
    return out


def build_vocab(matches: Iterable[MatchInfo]) -> Vocab:
    """Freeze the vocab from (training) matches. Sorted for determinism."""
    players: set[str] = set()
    maps: set[str] = set()
    formats: set[str] = set()
    for m in matches:
        for name, _ in resolved_real_players(m):
            players.add(name)
        maps.add(m.map)
        if m.composition is not None:
            formats.add(m.composition.category)
    return Vocab(
        player={name: i + 1 for i, name in enumerate(sorted(players))},
        map={name: i + 1 for i, name in enumerate(sorted(maps))},
        fmt={name: i + 1 for i, name in enumerate(sorted(formats))},
        general=_fixed_index(_GENERALS),
        faction=_fixed_index(_FACTIONS),
    )


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
        fmt=vocab.fmt_idx(match.composition.category if match.composition else None),
        team_a=teams[a_id],
        team_b=teams[b_id],
        label=1 if winner == a_id else 0,
        duration_minutes=match.duration_minutes,
    )
