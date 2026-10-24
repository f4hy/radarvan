import type { BracketMatchOutput } from "./bracketApi"

// Hand-built pages under public/hype/<slug>/. The players are checked as well
// as the match id so a new bracket reusing the id doesn't link an old page.
const HYPE_PAGES: {
  matchId: string
  players: [string, string]
  slug: string
}[] = [
  { matchId: "LB3-1", players: ["Modus", "CoreDawg"], slug: "modus-coredawg" },
  { matchId: "LB4-1", players: ["Modus", "Tytan"], slug: "modus-tytan" },
  { matchId: "LB5-1", players: ["Modus", "WildCard"], slug: "modus-wildcard" },
]

export function hypePageHref(match: BracketMatchOutput): string | null {
  const { player_a: a, player_b: b } = match
  if (a == null || b == null) return null
  const page = HYPE_PAGES.find(
    (p) =>
      p.matchId === match.match_id &&
      p.players.includes(a) &&
      p.players.includes(b),
  )
  // index.html explicitly: Vite's dev server won't resolve a public/ directory URL.
  return page ? `/hype/${page.slug}/index.html` : null
}
