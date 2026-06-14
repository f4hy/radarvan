"""MapData repository."""

from sqlalchemy import func, select

from ..api_types import MapDataPayload
from ..db import MapData

from .base import BaseRepo


def normalize_map_name(name: str) -> str:
    """Whitespace-insensitive, lowercased map-name key for matching."""
    return "".join(name.split()).lower()


class MapRepo(BaseRepo):
    """Operations on MapData (parsed map geometry)."""

    def save_map_data(self, map_name: str, payload: MapDataPayload) -> None:
        """Upsert map geometry data for the given map name."""
        row = MapData(map_name=map_name, data=payload.model_dump())
        self.session.merge(row)
        self._commit_if_auto()

    def get_map_data(self, map_name: str) -> MapDataPayload | None:
        """Return the map geometry payload (case- and whitespace-insensitive), or None."""
        row = self._find_map_data_row(map_name)
        if row is None:
            return None
        return MapDataPayload.model_validate(row.data)

    def _find_map_data_row(self, map_name: str) -> MapData | None:
        stmt = select(MapData).where(MapData.map_name.ilike(map_name))
        row = self.session.scalar(stmt)
        if row is not None:
            return row
        normalized = normalize_map_name(map_name)
        stmt = select(MapData).where(
            func.lower(func.replace(MapData.map_name, " ", "")) == normalized
        )
        return self.session.scalar(stmt)

    def resolve_map_name(self, map_name: str) -> str | None:
        """Return the canonical stored map_name matching the given input, or None."""
        row = self._find_map_data_row(map_name)
        return row.map_name if row is not None else None

    def list_maps_by_player_count(self) -> dict[int, list[str]]:
        """Return all known maps grouped by number of player starting positions."""
        rows = self.session.scalars(select(MapData)).all()
        result: dict[int, list[str]] = {}
        for row in rows:
            starts = row.data.get("player_starts")
            count = len(starts) if isinstance(starts, list) else 0
            result.setdefault(count, []).append(row.map_name)
        return {k: sorted(v) for k, v in sorted(result.items())}
