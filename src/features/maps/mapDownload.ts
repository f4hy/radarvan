// Map search + download helpers over the generated client.

import type { MapsByPlayerCount } from "../../api"
import { MapClient } from "../../clients/map"

export type MapOption = { name: string; playerCount: number }

// Every map with stored geometry (MapData row), flattened out of the
// player-count groups `/api/maps_by_player_count` returns - the same set that
// has a hosted `.map`/image in S3, so it's the right source for both search
// and download. Deduped: a map only ever has one player count, but the
// grouping shape allows repeats in principle.
export async function fetchMapOptions(): Promise<MapOption[]> {
  const groups: MapsByPlayerCount[] =
    await MapClient.getMapsByPlayerCountApiMapsByPlayerCountGet()
  const byName = new Map<string, number>()
  for (const group of groups) {
    for (const name of group.maps) {
      byName.set(name, group.playerCount)
    }
  }
  return [...byName.entries()]
    .map(([name, playerCount]) => ({ name, playerCount }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

function downloadURI(uri: string, name: string) {
  const link = document.createElement("a")
  link.download = name
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Fetches a presigned URL for the map's raw `.map` file and triggers the
// browser download. The save name is signed into the URL's
// Content-Disposition - `download` alone is ignored on a cross-origin (S3)
// href, same as the replay download in MatchCard.
export async function downloadMapFile(mapName: string): Promise<void> {
  const result = await MapClient.getMapDownloadApiMapDownloadMapNameGet({
    mapName,
  })
  downloadURI(result.url, result.filename)
}
