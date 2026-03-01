export function isDebug(): boolean {
  const params = new URLSearchParams(window.location.search)
  return !!params.get("debug")
}

export function winRate(wins: number, losses: number): number {
  const tot = wins + losses
  return tot > 0 ? wins / tot : 0
}
