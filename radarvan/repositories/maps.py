"""MapData repository."""

from datetime import UTC, datetime

from sqlalchemy import ColumnElement, func, select

from ..api_types import MapDataPayload
from ..db import MapData

from .base import BaseRepo


def normalize_map_name(name: str) -> str:
    """Whitespace-insensitive, lowercased map-name key for matching."""
    return "".join(name.split()).lower()


class MapRepo(BaseRepo):
    """Operations on MapData (parsed map geometry)."""

    def save_map_data(
        self,
        map_name: str,
        payload: MapDataPayload,
        crc: str | None = None,
        mapparse_bin_hash: str | None = None,
    ) -> None:
        """Upsert map geometry data (and optionally the CRC) for the given name.

        Loads-or-creates the row and sets only the fields provided, so a
        geometry save without a CRC leaves any existing CRC untouched (and vice
        versa via `set_map_crc`) - no `merge()`/`onupdate` NULL-clobber to guard.
        """
        row = self.session.get(MapData, map_name)
        if row is None:
            row = MapData(map_name=map_name)
            self.session.add(row)
        row.data = payload.model_dump()
        if crc is not None:
            row.crc = crc
        if mapparse_bin_hash is not None:
            row.mapparse_bin_hash = mapparse_bin_hash
        self._commit_if_auto()

    def delete_map_data(self, map_name: str) -> bool:
        """Delete the MapData row for a map (case-/whitespace-insensitive). False if none."""
        row = self._find_map_data_row(map_name)
        if row is None:
            return False
        self.session.delete(row)
        self._commit_if_auto()
        return True

    def set_map_crc(self, map_name: str, crc: str) -> bool:
        """Store the CRC on an existing MapData row. Returns False if no such row.

        Updates a loaded row in place (so it never clobbers `data`); callers that
        also have geometry should use `save_map_data(..., crc=...)` instead.
        """
        row = self._find_map_data_row(map_name)
        if row is None:
            return False
        row.crc = crc
        self._commit_if_auto()
        return True

    def get_map_crc(self, map_name: str) -> str | None:
        """Return the stored CRC for a map (case-/whitespace-insensitive), or None."""
        row = self._find_map_data_row(map_name)
        return row.crc if row is not None else None

    def list_map_names(self) -> list[str]:
        """Return every stored map_name."""
        return list(self.session.scalars(select(MapData.map_name)).all())

    def unsynced_maps(self, limit: int | None = None) -> list[tuple[str, str | None]]:
        """(map_name, crc) for maps not yet known to be on cncstats, by name.

        Excludes maps we've already pushed / confirmed present (cncstats_synced_at
        set), so a push run never re-sends them.
        """
        stmt = (
            select(MapData.map_name, MapData.crc)
            .where(MapData.cncstats_synced_at.is_(None))
            .order_by(MapData.map_name)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return [(name, crc) for name, crc in self.session.execute(stmt).all()]

    def _stale_mapparse_filter(self, current_hash: str) -> ColumnElement[bool]:
        return (MapData.mapparse_bin_hash.is_(None)) | (
            MapData.mapparse_bin_hash != current_hash
        )

    def maps_needing_reparse(
        self, current_hash: str, limit: int | None = None
    ) -> list[str]:
        """map_name for rows whose stored geometry predates `current_hash`.

        A row with no hash at all (parsed before this column existed) counts as
        stale too. Ordered by map_name for a deterministic, resumable backfill.
        """
        stmt = (
            select(MapData.map_name)
            .where(self._stale_mapparse_filter(current_hash))
            .order_by(MapData.map_name)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_maps_needing_reparse(self, current_hash: str) -> int:
        """Total rows whose stored geometry predates `current_hash`."""
        stmt = select(func.count()).select_from(MapData).where(
            self._stale_mapparse_filter(current_hash)
        )
        return self.session.scalar(stmt) or 0

    def record_cncstats_sync(self, map_name: str, crc: str) -> bool:
        """Mark a map as present on cncstats (and store its CRC). False if no row."""
        row = self.session.get(MapData, map_name)
        if row is None:
            return False
        row.crc = crc
        row.cncstats_synced_at = datetime.now(UTC)
        self._commit_if_auto()
        return True

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
