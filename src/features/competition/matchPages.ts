import type { BracketMatchOutput } from "./bracketApi"

export type MatchPageKind = "preview" | "recap"

// Hand-built pages: previews under public/hype/<slug>/, recaps under
// public/recap/<slug>/. The players are checked as well as the match id so a
// new bracket reusing the id doesn't link an old page.
const MATCH_PAGES: {
  matchId: string
  players: [string, string]
  kind: MatchPageKind
  slug: string
}[] = [
  {
    matchId: "LB3-1",
    players: ["Modus", "CoreDawg"],
    kind: "preview",
    slug: "modus-coredawg",
  },
  {
    matchId: "LB4-1",
    players: ["Modus", "Tytan"],
    kind: "preview",
    slug: "modus-tytan",
  },
  {
    matchId: "LB4-1",
    players: ["Modus", "Tytan"],
    kind: "recap",
    slug: "modus-tytan",
  },
  {
    matchId: "LB5-1",
    players: ["Modus", "WildCard"],
    kind: "preview",
    slug: "modus-wildcard",
  },
]

// A preview only until the match is played, a recap only after.
export function matchPageLink(
  match: BracketMatchOutput,
): { kind: MatchPageKind; href: string } | null {
  const { player_a: a, player_b: b } = match
  if (a == null || b == null) return null
  const kind: MatchPageKind = match.status === "completed" ? "recap" : "preview"
  const page = MATCH_PAGES.find(
    (p) =>
      p.kind === kind &&
      p.matchId === match.match_id &&
      p.players.includes(a) &&
      p.players.includes(b),
  )
  if (!page) return null
  const dir = kind === "recap" ? "recap" : "hype"
  // index.html explicitly: Vite's dev server won't resolve a public/ directory URL.
  return { kind, href: `/${dir}/${page.slug}/index.html` }
}
