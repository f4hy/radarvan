import type { MapData } from "../api"
import { winRate } from "./utils"

// Shared by MapStats (pivoted by map) and GeneralStats (pivoted by general) -
// both read the same `/api/map_stats` payload, just grouped along a different
// axis, so the derivation lives once here.
export const MIN_SUMMARY_GAMES = 3

export interface MapEntry {
  mapName: string
  wins: number
  losses: number
}

export interface BestWorst {
  best: MapEntry
  worst: MapEntry
}

export function computeGeneralBestWorst(
  maps: MapData[],
): Array<[number, BestWorst]> {
  const acc = new Map<
    number,
    { best: MapEntry | null; worst: MapEntry | null }
  >()
  for (const map of maps) {
    for (const g of map.generalStats) {
      if (g.wins + g.losses < MIN_SUMMARY_GAMES) continue
      const wr = winRate(g.wins, g.losses)
      const entry: MapEntry = {
        mapName: map.mapName,
        wins: g.wins,
        losses: g.losses,
      }
      const cur = acc.get(g.general) ?? { best: null, worst: null }
      if (!cur.best || wr > winRate(cur.best.wins, cur.best.losses))
        cur.best = entry
      if (!cur.worst || wr < winRate(cur.worst.wins, cur.worst.losses))
        cur.worst = entry
      acc.set(g.general, cur)
    }
  }
  const result: Array<[number, BestWorst]> = []
  for (const [g, bw] of acc.entries()) {
    if (bw.best && bw.worst && bw.best.mapName !== bw.worst.mapName) {
      result.push([g, { best: bw.best, worst: bw.worst }])
    }
  }
  result.sort(
    ([, a], [, b]) =>
      winRate(b.best.wins, b.best.losses) - winRate(a.best.wins, a.best.losses),
  )
  return result
}
