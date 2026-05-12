export function isDebug(): boolean {
  const params = new URLSearchParams(window.location.search)
  return !!params.get("debug")
}

export function winRate(wins: number, losses: number): number {
  const tot = wins + losses
  return tot > 0 ? wins / tot : 0
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
  }
  if (colorName === "-1") return "#000000"
  const mapped = colorMap[colorName.toLowerCase()]
  if (mapped) return mapped
  if (/^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(colorName)) return colorName
  if (/^(rgb|rgba|hsl|hsla|color)\(/i.test(colorName)) return colorName
  return "#808080"
}

export function buildPlayerColorMap(
  playerSummaries: Array<{ name: string; color: string }>,
  transform: (color: string) => string = (c) => c,
): Record<string, string> {
  return Object.fromEntries(
    playerSummaries.map((ps) => [ps.name, transform(ps.color)]),
  )
}
