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
  {
    matchId: "LB5-1",
    players: ["Modus", "WildCard"],
    kind: "recap",
    slug: "modus-wildcard",
  },
  {
    matchId: "GF-1",
    players: ["Gorn", "Modus"],
    kind: "preview",
    slug: "modus-gorn",
  },
  {
    matchId: "GF-1",
    players: ["Gorn", "Modus"],
    kind: "recap",
    slug: "modus-gorn",
  },
  {
    matchId: "GF-2",
    players: ["Gorn", "Modus"],
    kind: "preview",
    slug: "modus-gorn-reset",
  },
  {
    matchId: "GF-2",
    players: ["Gorn", "Modus"],
    kind: "recap",
    slug: "modus-gorn-reset",
  },
]

// The whole-tournament write-up, tied to the final it ends on.
const STORY_PAGES: Record<string, string> = {
  "modus-gorn-reset": "/recap/2026-1v1-bracket/index.html",
}

// A preview only until the match is played, a recap only after.
export function matchPageLink(
  match: BracketMatchOutput,
): { kind: MatchPageKind; href: string } | null {
  const page = findPage(match)
  if (!page) return null
  const dir = page.kind === "recap" ? "recap" : "hype"
  // index.html explicitly: Vite's dev server won't resolve a public/ directory URL.
  return { kind: page.kind, href: `/${dir}/${page.slug}/index.html` }
}

function findPage(match: BracketMatchOutput) {
  const { player_a: a, player_b: b } = match
  if (a == null || b == null) return undefined
  const kind: MatchPageKind = match.status === "completed" ? "recap" : "preview"
  return MATCH_PAGES.find(
    (p) =>
      p.kind === kind &&
      p.matchId === match.match_id &&
      p.players.includes(a) &&
      p.players.includes(b),
  )
}

// Links for a finished bracket: the recap of its last Grand Final match, and
// the tournament story when one was written for that final.
export function championPageLinks(
  matches: BracketMatchOutput[],
): { finalRecap: string; story: string | null } | null {
  const final = matches
    .filter((m) => m.bracket === "GF" && m.status === "completed")
    .at(-1)
  const page = final && findPage(final)
  if (!page) return null
  return {
    finalRecap: `/recap/${page.slug}/index.html`,
    story: STORY_PAGES[page.slug] ?? null,
  }
}
