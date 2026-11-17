import type { BracketFactionGame, PlayerWL } from "../../api/types.gen"
import type { General } from "../../lib/General"
import { FACTIONS, type Faction, generalFaction } from "../../lib/general_utils"
import { winRate } from "../../lib/utils"

export type Grain = "general" | "faction"

// A side of a matchup at the chosen grain: a general, or a whole faction.
export type Side = General | Faction

export const SIDE_ORDER: Record<Grain, Side[]> = {
  general: FACTIONS.flatMap((f) => f.generals),
  faction: FACTIONS.map((f) => f.faction),
}

export function sideOf(general: General, grain: Grain): Side | undefined {
  return grain === "general" ? general : generalFaction(general)
}

type WL = { wins: number; losses: number }

export const sumWL = (rows: WL[]): WL => ({
  wins: rows.reduce((n, r) => n + r.wins, 0),
  losses: rows.reduce((n, r) => n + r.losses, 0),
})

export type Matchup = {
  a: Side
  b: Side
  aWins: number
  bWins: number
  games: BracketFactionGame[]
}

const rank = (grain: Grain, side: Side) => SIDE_ORDER[grain].indexOf(side)

// Each pairing once, its sides in SIDE_ORDER; busiest first. In a mirror
// every game is a win for `a`.
export function matchups(games: BracketFactionGame[], grain: Grain): Matchup[] {
  const byPair = new Map<string, Matchup>()
  for (const game of games) {
    const w = sideOf(game.winnerGeneral, grain)
    const l = sideOf(game.loserGeneral, grain)
    if (w === undefined || l === undefined) continue
    const [a, b] = rank(grain, w) <= rank(grain, l) ? [w, l] : [l, w]
    const key = `${a}|${b}`
    const row = byPair.get(key) ?? {
      a,
      b,
      aWins: 0,
      bWins: 0,
      games: [],
    }
    if (w === a) row.aWins += 1
    else row.bWins += 1
    row.games.push(game)
    byPair.set(key, row)
  }
  return [...byPair.values()].sort(
    (x, y) =>
      y.games.length - x.games.length ||
      rank(grain, x.a) - rank(grain, y.a) ||
      rank(grain, x.b) - rank(grain, y.b),
  )
}

export type SetLoserRecord = {
  side: Side
  wins: number
  losses: number
  players: PlayerWL[]
}

// The record of whoever lost each game's set, on the side they played that
// game. Unscored sets are left out.
export function setLoserRecords(
  games: BracketFactionGame[],
  grain: Grain,
): SetLoserRecord[] {
  const bySide = new Map<Side, Map<string, PlayerWL>>()
  for (const game of games) {
    if (game.winnerLostSet == null) continue
    const won = game.winnerLostSet
    const side = sideOf(won ? game.winnerGeneral : game.loserGeneral, grain)
    if (side === undefined) continue
    const player = won ? game.winner : game.loser
    const players = bySide.get(side) ?? new Map<string, PlayerWL>()
    const wl = players.get(player) ?? { player, wins: 0, losses: 0 }
    players.set(player, {
      player,
      wins: wl.wins + (won ? 1 : 0),
      losses: wl.losses + (won ? 0 : 1),
    })
    bySide.set(side, players)
  }
  return [...bySide.entries()]
    .map(([side, players]) => {
      const list = [...players.values()].sort(
        (x, y) =>
          y.wins + y.losses - (x.wins + x.losses) ||
          y.wins - x.wins ||
          x.player.localeCompare(y.player),
      )
      return {
        side,
        ...sumWL(list),
        players: list,
      }
    })
    .sort(
      (x, y) =>
        winRate(y.wins, y.losses) - winRate(x.wins, x.losses) ||
        y.wins + y.losses - (x.wins + x.losses) ||
        rank(grain, x.side) - rank(grain, y.side),
    )
}
