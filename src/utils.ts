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

// Format a 0..1 fraction as a whole-number percent, e.g. 0.732 -> "73%".
export function formatPercent(fraction: number): string {
  return `${(fraction * 100).toFixed(0)}%`
}

// Strip the directory path and ".map" extension from a map name/path for display.
export function displayMapName(name: string): string {
  return (name.split("/").pop() ?? name).replace(/\.map$/i, "")
}

export function getColorHex(colorName: string): string {
  const colorMap: { [key: string]: string } = {
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
  if (colorName === "-1") return "#000000"
  const mapped = colorMap[colorName.toLowerCase()]
  if (mapped) return mapped
  if (/^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(colorName)) return colorName
  if (/^(rgb|rgba|hsl|hsla|color)\(/i.test(colorName)) return colorName
  return "#808080"
}

// Black or white, whichever reads better on a given hex background - actual
// game colors (unlike the curated PLAYER_HUE_PALETTE below) include light
// hues like yellow/gold/pink/silver where white text would wash out.
export function contrastTextColor(hex: string): string {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex)
  if (!m) return "#fff"
  const full =
    m[1].length === 3
      ? m[1]
          .split("")
          .map((c) => c + c)
          .join("")
      : m[1]
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.6 ? "#000" : "#fff"
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
