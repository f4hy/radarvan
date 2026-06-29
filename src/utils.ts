export function winRate(wins: number, losses: number): number {
  const tot = wins + losses
  return tot > 0 ? wins / tot : 0
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
