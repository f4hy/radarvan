import type { MapPoint, Player } from "./api"
import { PlayerRole, Team } from "./api"
import { LOSS_COLOR, NEUTRAL_COLOR, WIN_COLOR } from "./theme"

// The generated PlayerRole is NUMBER_0/1/2 - Python IntEnum member names don't
// survive into the OpenAPI schema (same reason Team is NUMBER_MINUS_1). Alias
// them so call sites read as something other than magic numbers.
export const PLAYER_ROLE = {
  HUMAN: PlayerRole.NUMBER_0,
  CPU: PlayerRole.NUMBER_1,
  OBSERVER: PlayerRole.NUMBER_2,
} as const

/** True for a spectator slot - someone in the lobby who didn't play.
 *
 * Prefer this over inspecting `team`. Observer-ness lives in `role`, which the
 * backend derives from the replay header; `team` only carries it for matches
 * re-parsed since that fix, so most historical observers still sit on team 0
 * and a `team === -1` check misses them. `role` is null only for the handful of
 * rows the backfill couldn't classify, hence the fallback.
 */
export function isObserver(p: Player): boolean {
  if (p.role != null) return p.role === PLAYER_ROLE.OBSERVER
  return p.team === Team.NUMBER_MINUS_1
}

/** True for anyone who actually played - humans and AI, observers excluded. */
export function isCompetitor(p: Player): boolean {
  return !isObserver(p)
}

const compactCash = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})

// Format a dollar amount compactly, e.g. 1400000 -> "$1.4M".
export function formatCash(amount: number): string {
  return `$${compactCash.format(amount)}`
}

// Sum of cash available across a map's supply piles (mapparse's `supply`
// category, MapPoint.amount) - the total money on the map to collect, not
// what any player actually gathered.
export function totalMapSupply(supply: MapPoint[] | undefined): number {
  return (supply ?? []).reduce((sum, p) => sum + (p.amount ?? 0), 0)
}

export function winRate(wins: number, losses: number): number {
  const tot = wins + losses
  return tot > 0 ? wins / tot : 0
}

// Below this many games a win rate is treated as too noisy to trust — used to
// dim/grey such cells so a 1-0 record doesn't read as a confident 100%.
export const LOW_SAMPLE_GAMES = 5

// Wilson score interval for a binomial proportion (default z = 1.96 → 95% CI).
// Unlike the naive wins/n, it accounts for sample size: small n yields a wide
// interval pulled toward 0.5. `rate` is the point estimate; `low`/`high` are the
// confidence bounds; all in 0..1. Returns a degenerate interval for n = 0.
export function wilsonInterval(
  wins: number,
  losses: number,
  z = 1.96,
): { rate: number; low: number; high: number; n: number } {
  const n = wins + losses
  if (n <= 0) return { rate: 0, low: 0, high: 0, n: 0 }
  const phat = wins / n
  const z2 = z * z
  const denom = 1 + z2 / n
  const center = (phat + z2 / (2 * n)) / denom
  const margin = (z * Math.sqrt((phat * (1 - phat) + z2 / (4 * n)) / n)) / denom
  return {
    rate: phat,
    low: Math.max(0, center - margin),
    high: Math.min(1, center + margin),
    n,
  }
}

// The Wilson lower bound — the statistically-honest key for ranking win rates
// ("how not to sort by average rating"): a 9-1 record outranks a 1-0 one
// because we're more confident it's genuinely good.
export function wilsonLowerBound(wins: number, losses: number): number {
  return wilsonInterval(wins, losses).low
}

// Above this many games a record is treated as fully sampled — the point where
// `confidence` below saturates at 1.
const FULL_SAMPLE_GAMES = 15

export type WinRateToneName = "positive" | "negative" | "inconclusive"

export interface WinRateVerdict {
  /** Which side of even the record is on, once uncertainty is accounted for. */
  tone: WinRateToneName
  /** MUI palette key, for `color=` on Chip / LinearProgress / Alert. */
  muiColor: "success" | "error" | "inherit"
  /** Solid hex, for sx values and recharts (which can't read the theme). */
  hex: string
  /** 0..1 by sample size — how loudly to render the verdict (opacity, alpha). */
  confidence: number
  /** 0..1 by distance from even — 0 at 50%, 1 at 0% or 100%. */
  margin: number
  rate: number
  low: number
  high: number
  n: number
  /** Too few games to read as anything; render dimmed. */
  lowSample: boolean
}

/**
 * The single rule for "is this win rate good?".
 *
 * Color comes from the 95% Wilson interval, not the raw rate: green only when
 * we're confident the record is above even, red only when confident it's below,
 * neutral when the sample can't tell us — which is exactly the case a naive
 * threshold gets loudly wrong (a 3-0 record is not a 100% player).
 *
 * This used to be spelled four different ways across the app: a 0.55/0.45
 * threshold copy-pasted into TeamStats and MapStats, an rgb() ramp in Matches,
 * and an alpha tint in GameNight — so the same record read green on one page
 * and grey on another. Everything routes through here now; `confidence` and
 * `margin` are separate so a caller can pick which one drives its intensity
 * without inventing a second rule.
 */
export function winRateTone(wins: number, losses: number): WinRateVerdict {
  const { rate, low, high, n } = wilsonInterval(wins, losses)
  const tone: WinRateToneName =
    n > 0 && low > 0.5
      ? "positive"
      : n > 0 && high < 0.5
        ? "negative"
        : "inconclusive"
  return {
    tone,
    muiColor:
      tone === "positive"
        ? "success"
        : tone === "negative"
          ? "error"
          : "inherit",
    hex:
      tone === "positive"
        ? WIN_COLOR
        : tone === "negative"
          ? LOSS_COLOR
          : NEUTRAL_COLOR,
    confidence: Math.min(1, n / FULL_SAMPLE_GAMES),
    margin: Math.min(1, Math.abs(rate - 0.5) * 2),
    rate,
    low,
    high,
    n,
    lowSample: n < LOW_SAMPLE_GAMES,
  }
}

// Format a 0..1 fraction as a whole-number percent, e.g. 0.732 -> "73%".
export function formatPercent(fraction: number): string {
  return `${(fraction * 100).toFixed(0)}%`
}

// Strip the directory path and ".map" extension from a map name/path for display.
export function displayMapName(name: string): string {
  return (name.split("/").pop() ?? name).replace(/\.map$/i, "")
}

// Module scope, not rebuilt per call: getColorHex runs once per player per
// chart series on every render.
const COLOR_MAP: { [key: string]: string } = {
  pink: "#FFC0CB",
  red: "#FF0000",
  blue: "#0000FF",
  skyblue: "#87CEEB",
  green: "#00FF00",
  yellow: "#FFFF00",
  purple: "#800080",
  orange: "#FFA500",
  gold: "#FFD700",
  black: "#212121",
  lime: "#BFFF00",
  silver: "#C0C0C0",
  maroon: "#800000",
  metallicgrey: "#808080",
  violet: "#7F00FF",
}

export function getColorHex(colorName: string): string {
  if (colorName === "-1") return "#000000"
  const mapped = COLOR_MAP[colorName.toLowerCase()]
  if (mapped) return mapped
  if (/^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(colorName)) return colorName
  if (/^(rgb|rgba|hsl|hsla|color)\(/i.test(colorName)) return colorName
  return "#808080"
}

// Stable, deterministic color for a player name, so the same player reads as
// the same color everywhere (team stats, records, leaderboards). Uses a fixed
// palette of readable, saturated hues picked by hashing the name.
const PLAYER_HUE_PALETTE = [
  "#2f6df0",
  "#7c4dff",
  "#00897b",
  "#e0457b",
  "#f5871f",
  "#3949ab",
  "#0b8043",
  "#c2185b",
  "#00838f",
  "#5e35b1",
  "#d81b60",
  "#1565c0",
]

export function playerColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0
  }
  const idx = Math.abs(hash) % PLAYER_HUE_PALETTE.length
  return PLAYER_HUE_PALETTE[idx]
}

export function buildPlayerColorMap(
  playerSummaries: Array<{ name: string; color: string }>,
  transform: (color: string) => string = (c) => c,
): Record<string, string> {
  return Object.fromEntries(
    playerSummaries.map((ps) => [ps.name, transform(ps.color)]),
  )
}
